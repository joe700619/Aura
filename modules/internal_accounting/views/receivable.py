from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.contrib import messages
import json
from django.utils import timezone
from ..models import Receivable, PaymentRecord, Voucher, VoucherDetail, Account, ReceivableFeeApportion
from ..forms import ReceivableForm, PaymentRecordFormSet, ReceivableFeeApportionFormSet

def generate_voucher_for_receivable(receivable, user):
    """
    Generates a Voucher and associated VoucherDetails from a posted Receivable and its Collections.
    Mirrors the frontend JS logic in voucher_preview_modal.html.
    """
    if receivable.outstanding_balance > 0:
        raise ValueError("尚有未收款項，無法過帳產生傳票")

    company_vat = receivable.unified_business_no or ''

    # Define account mappings based on frontend logic
    account_mapping = {
        '2190': '預收款項',
        '1123': '應收帳款',
        '111401': "國泰世華", # or 銀行存款
        '111403': '綠界',
        '1110': '現金',
        '1124': '應收票據',
        '1149': '扣繳稅款',
        '613201': '手續費',
        '6123': '呆帳損失',
    }
    
    # Pre-fetch required accounts
    accounts = {code: Account.objects.filter(code=code).first() for code in account_mapping.keys()}
    missing_accounts = [code for code, acc in accounts.items() if not acc]
    if missing_accounts:
        raise ValueError(f"系統缺少必要的會計科目代碼：{', '.join(missing_accounts)}，請先至會計科目管理新增。")

    entries = []

    for col in receivable.collections.all():
        if col.is_posted:
            if col.total > 0:
                entries.append({'type': 'debit', 'account': accounts['2190'], 'amount': col.total, 'remark': '預收款沖轉'})
        else:
            # Map method to account
            method_code = '111401'
            if col.method == 'bank':
                method_code = '111401'
            elif col.method == 'ecpay':
                method_code = '111403'
            elif col.method == 'cash':
                method_code = '1110'
            elif col.method == 'notes':
                method_code = '1124'
            
            if not accounts.get(method_code):
                raise ValueError(f"缺少會計科目代碼: {method_code}")

            if col.amount > 0:
                entries.append({'type': 'debit', 'account': accounts[method_code], 'amount': col.amount, 'remark': '收款'})
            if col.tax > 0:
                entries.append({'type': 'debit', 'account': accounts['1149'], 'amount': col.tax, 'remark': '扣繳稅款'})
            if col.fee > 0:
                entries.append({'type': 'debit', 'account': accounts['613201'], 'amount': col.fee, 'remark': '手續費'})
            if col.allowance > 0:
                entries.append({'type': 'debit', 'account': accounts['6123'], 'amount': col.allowance, 'remark': '折讓'})
            
            # Mark the collection as posted
            col.is_posted = True
            col.save(update_fields=['is_posted'])

    total_debits = sum(e['amount'] for e in entries)
    
    if total_debits > 0:
        entries.append({'type': 'credit', 'account': accounts['1123'], 'amount': total_debits, 'remark': '應收帳款沖帳'})

    if not entries:
        return None

    # Create the Voucher
    today = timezone.now().date()
    today_str = today.strftime('%Y%m%d')
    count = Voucher.objects.filter(date=today).count() + 1
    voucher_no = f'VOU-{today_str}-{count:03d}'

    voucher = Voucher.objects.create(
        date=today,
        voucher_no=voucher_no,
        description=f"應收帳款過帳: {receivable.company_name}",
        status=Voucher.Status.DRAFT,
        source=Voucher.Source.SYSTEM,
        created_by=user
    )

    # Create the Details
    for entry in entries:
        # Determine auxiliary fields
        company_id = ''
        if entry['account'].auxiliary_type == 'PARTNER':
            company_id = company_vat

        VoucherDetail.objects.create(
            voucher=voucher,
            account=entry['account'],
            debit=entry['amount'] if entry['type'] == 'debit' else 0,
            credit=entry['amount'] if entry['type'] == 'credit' else 0,
            company_id=company_id,
            remark=entry['remark']
        )
    
    return voucher

class ReceivableListView(LoginRequiredMixin, ListView):
    model = Receivable
    template_name = 'receivable/list.html'
    context_object_name = 'receivables'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '應收帳款管理'
        context['model_name'] = 'internal_accounting:receivable'
        context['model_app_label'] = 'internal_accounting'
        context['create_button_label'] = '新增應收帳款'
        return context

class ReceivableCreateView(LoginRequiredMixin, CreateView):
    model = Receivable
    form_class = ReceivableForm
    template_name = 'receivable/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:receivable_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增應收帳款'
        context['action'] = 'create'
        context['collections'] = []
        if self.request.POST:
            context['fee_apportion_formset'] = ReceivableFeeApportionFormSet(self.request.POST)
        else:
            context['fee_apportion_formset'] = ReceivableFeeApportionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        fee_apportion_formset = context['fee_apportion_formset']
        
        if form.is_valid() and fee_apportion_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                fee_apportion_formset.instance = self.object
                fee_apportion_formset.save()
            messages.success(self.request, "應收帳款已建立")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

class ReceivableUpdateView(LoginRequiredMixin, UpdateView):
    model = Receivable
    form_class = ReceivableForm
    template_name = 'receivable/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:receivable_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯應收帳款: {self.object.company_name}'
        context['action'] = 'update'
        context['collections'] = self.object.collections.all().order_by('-date', '-collection_no')
        
        if self.request.POST:
            context['fee_apportion_formset'] = ReceivableFeeApportionFormSet(self.request.POST, instance=self.object)
        else:
            context['fee_apportion_formset'] = ReceivableFeeApportionFormSet(instance=self.object)

        # History Logic for Sidebar
        if self.object and hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or "資料變更",
                })
            context['history'] = history_list

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        fee_apportion_formset = context['fee_apportion_formset']
        
        if form.is_valid() and fee_apportion_formset.is_valid():
            # Check if is_posted is changing from False to True
            was_posted = form.initial.get('is_posted', False)
            is_posted_now = form.cleaned_data.get('is_posted', False)
            is_newly_posted = (not was_posted) and is_posted_now

            with transaction.atomic():
                self.object = form.save()
                fee_apportion_formset.instance = self.object
                fee_apportion_formset.save()

                if is_newly_posted:
                    try:
                        voucher = generate_voucher_for_receivable(self.object, self.request.user)
                        if voucher:
                            messages.success(self.request, f"應收帳款已更新，並成功產生傳票：{voucher.voucher_no}")
                        else:
                            messages.warning(self.request, "應收帳款已過帳，但無金額可產生傳票分錄。")
                    except ValueError as e:
                        self.object.is_posted = False
                        self.object.save(update_fields=['is_posted'])
                        messages.error(self.request, f"產生傳票失敗：{str(e)}。已取消過帳狀態。")
                    except Exception as e:
                        self.object.is_posted = False
                        self.object.save(update_fields=['is_posted'])
                        messages.error(self.request, f"產生傳票時發生未知的系統錯誤：{str(e)}")
                else:
                    if is_posted_now:
                        messages.success(self.request, "應收帳款已更新，狀態已為過帳 (未拋轉新傳票)")
                    else:
                        messages.success(self.request, "應收帳款已更新 (未勾選過帳)")
                
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

class ReceivableDeleteView(LoginRequiredMixin, DeleteView):
    model = Receivable
    template_name = 'receivable/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:receivable_list')
