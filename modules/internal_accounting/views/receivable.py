import random
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from ..models import Receivable
from ..forms import ReceivableForm, ReceivableFeeApportionFormSet
from core.mixins import BusinessRequiredMixin, PrevNextMixin, ListActionMixin, SearchMixin, SoftDeleteMixin, FilterMixin


class ReceivableListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = Receivable
    template_name = 'receivable/list.html'
    context_object_name = 'receivables'
    paginate_by = 25
    search_fields = ['company_name', 'unified_business_no', 'receivable_no']
    # status is a Python property → use filter_property
    filter_property = 'status'
    filter_choices = {
        '未收款':  {},
        '部分收款': {},
        '已結清':  {},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().prefetch_related('collections')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '應收帳款管理'
        context['custom_create_url'] = reverse_lazy('internal_accounting:receivable_create')
        context['create_button_label'] = '新增應收帳款'
        context['count_all']     = context['filter_counts']['ALL']
        context['count_unpaid']  = context['filter_counts']['未收款']
        context['count_partial'] = context['filter_counts']['部分收款']
        context['count_settled'] = context['filter_counts']['已結清']
        return context


class ReceivableCreateView(BusinessRequiredMixin, CreateView):
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


class ReceivableUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = Receivable
    form_class = ReceivableForm
    template_name = 'receivable/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:receivable_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯應收帳款: {self.object.company_name}'
        context['action'] = 'update'
        context['collections'] = self.object.collections.filter(is_deleted=False).order_by('-date', '-collection_no')

        if self.request.POST:
            context['fee_apportion_formset'] = ReceivableFeeApportionFormSet(self.request.POST, instance=self.object)
        else:
            context['fee_apportion_formset'] = ReceivableFeeApportionFormSet(instance=self.object)

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
            with transaction.atomic():
                self.object = form.save()
                fee_apportion_formset.instance = self.object
                fee_apportion_formset.save()
            messages.success(self.request, "應收帳款已更新")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class ReceivableDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = Receivable
    template_name = 'receivable/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:receivable_list')


class GenerateReceivablePaymentLinkView(BusinessRequiredMixin, View):
    """產生應收帳款的綠界付款連結"""

    def post(self, request, pk):
        from modules.payment.models import PaymentTransaction

        receivable = get_object_or_404(Receivable, pk=pk, is_deleted=False)

        outstanding = int(receivable.outstanding_balance)
        if outstanding <= 0:
            return JsonResponse({'error': '應收餘額為零或已結清，無法產生付款連結。'}, status=400)

        random_suffix = f"{random.randint(0, 9999):04d}"
        base_no = (receivable.receivable_no or str(receivable.pk)).replace('-', '')
        merchant_trade_no = f"{base_no}{random_suffix}"[:20]

        PaymentTransaction.objects.create(
            merchant_trade_no=merchant_trade_no,
            total_amount=outstanding,
            trade_desc=f"應收帳款 {receivable.receivable_no or receivable.pk}",
            item_name=f"服務費用 ({receivable.company_name})"[:200],
            payment_type=PaymentTransaction.PaymentType.ECPAY,
            related_app='internal_accounting',
            related_model='Receivable',
            related_id=str(receivable.pk),
        )

        base_url = f"{request.scheme}://{request.get_host()}"
        pay_url = f"{base_url}/payment/bill/{merchant_trade_no}/"
        return JsonResponse({'url': pay_url})
