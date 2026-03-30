from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models as db_models
from django.db import transaction
from django.forms import ModelForm, HiddenInput
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from core.mixins import ListActionMixin
from ..models import BookkeepingClient, ClientBill
from modules.administrative.models import AdvancePaymentDetail
from modules.internal_accounting.services import ReceivableTransferService


class BookkeepingClientSearchView(LoginRequiredMixin, View):
    """API: 搜尋記帳客戶，回傳 JSON 供帳單選客戶 modal 使用"""

    def get(self, request):
        q = request.GET.get('q', '').strip()
        qs = BookkeepingClient.objects.filter(is_deleted=False).select_related(
            'bookkeeping_assistant', 'group_assistant'
        ).prefetch_related('service_fees')
        if q:
            qs = qs.filter(
                db_models.Q(name__icontains=q) | db_models.Q(tax_id__icontains=q)
            )
        qs = qs.order_by('name')[:30]

        data = []
        for client in qs:
            active_fee = (
                client.service_fees.filter(end_date__isnull=True)
                .order_by('-effective_date')
                .first()
            )
            if not active_fee:
                active_fee = client.service_fees.order_by('-effective_date').first()

            data.append({
                'id': client.pk,
                'name': client.name,
                'tax_id': client.tax_id or '',
                'cost_sharing_data': client.cost_sharing_data or [],
                'bookkeeping_assistant_name': (
                    client.bookkeeping_assistant.name if client.bookkeeping_assistant else ''
                ),
                'group_assistant_name': (
                    client.group_assistant.name if client.group_assistant else ''
                ),
                'billing_cycle_display': (
                    active_fee.get_billing_cycle_display() if active_fee else ''
                ),
                'service_fee': active_fee.service_fee if active_fee else 0,
                'ledger_fee': active_fee.ledger_fee if active_fee else 0,
            })

        return JsonResponse(data, safe=False)

class ClientBillForm(ModelForm):
    class Meta:
        model = ClientBill
        fields = ['client', 'year', 'month', 'bill_date', 'due_date', 'status', 'notes', 'is_posted', 'quotation_data', 'cost_sharing_data', 'advance_payment_data']
        widgets = {
            'quotation_data': HiddenInput(),
            'cost_sharing_data': HiddenInput(),
            'advance_payment_data': HiddenInput(),
        }


class FetchUnbilledAdvancePaymentsView(LoginRequiredMixin, View):
    def get(self, request, client_pk):
        from django.http import JsonResponse
        from modules.administrative.models import AdvancePaymentDetail
        client = get_object_or_404(BookkeepingClient, pk=client_pk)
        if not client.tax_id:
            return JsonResponse([], safe=False)
            
        details = AdvancePaymentDetail.objects.filter(
            unified_business_no=client.tax_id,
            is_billed=False,
            is_customer_absorbed=True
        ).select_related('advance_payment')
        
        data = []
        for detail in details:
            data.append({
                'id': detail.id,
                'date': detail.advance_payment.date.strftime('%Y-%m-%d'),
                'advance_no': detail.advance_payment.advance_no,
                'reason': detail.reason or '',
                'amount': int(detail.amount),
                'is_billed': detail.is_billed,
                'payment_type': detail.get_payment_type_display() if detail.payment_type else '',
                'url': detail.advance_payment.get_absolute_url()
            })
            
        return JsonResponse(data, safe=False)


class ClientBillListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = ClientBill
    template_name = 'bookkeeping/billing/list.html'
    context_object_name = 'bills'
    create_button_label = '新增帳單'

    def get_queryset(self):
        return super().get_queryset().filter(
            is_deleted=False
        ).select_related('client')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Supply custom_create_url because model_name 'clientbill' doesn't match 'bill_create' URL
        context['custom_create_url'] = reverse_lazy('bookkeeping:bill_create')
        return context


class ClientBillCreateView(LoginRequiredMixin, CreateView):
    model = ClientBill
    form_class = ClientBillForm
    template_name = 'bookkeeping/billing/form.html'
    success_url = reverse_lazy('bookkeeping:bill_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ClientBill.BillStatus.choices
        return context

    def get_success_url(self):
        return reverse_lazy('bookkeeping:bill_update', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            self.object.recalculate_total()
            
            try:
                import json
                new_data = self.object.advance_payment_data or []
                if isinstance(new_data, str):
                    new_data = json.loads(new_data)
                
                new_ap_ids = {int(item.get('id')) for item in new_data if item.get('id')}
                if new_ap_ids:
                    AdvancePaymentDetail.objects.filter(id__in=new_ap_ids).update(is_billed=True)
                    
                    # Mutate JSON so UI shows correct state
                    mutated = False
                    for item in new_data:
                        if not item.get('is_billed'):
                            item['is_billed'] = True
                            mutated = True
                    if mutated:
                        self.object.advance_payment_data = new_data
                        self.object.save(update_fields=['advance_payment_data'])
            except Exception as e:
                import traceback
                traceback.print_exc()

        messages.success(self.request, f'帳單 {self.object.bill_no} 建立成功！')
        return redirect(self.get_success_url())


class ClientBillUpdateView(LoginRequiredMixin, UpdateView):
    model = ClientBill
    form_class = ClientBillForm
    template_name = 'bookkeeping/billing/form.html'
    success_url = reverse_lazy('bookkeeping:bill_list')

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ClientBill.BillStatus.choices
        if self.object and self.object.client_id:
            active_fee = (
                self.object.client.service_fees
                .filter(end_date__isnull=True)
                .order_by('-effective_date')
                .first()
            )
            if not active_fee:
                active_fee = (
                    self.object.client.service_fees
                    .order_by('-effective_date')
                    .first()
                )
            context['client_service_fee'] = active_fee
        return context

    def get_success_url(self):
        return reverse_lazy('bookkeeping:bill_update', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        import json
        old_ap_ids = set()
        try:
            import json
            old_bill = ClientBill.objects.get(pk=self.object.pk)
            old_data = old_bill.advance_payment_data or []
            if isinstance(old_data, str):
                old_data = json.loads(old_data)
            old_ap_ids = {int(item.get('id')) for item in old_data if item.get('id')}
        except Exception:
            pass

        with transaction.atomic():
            self.object = form.save()
            self.object.recalculate_total()
            
            try:
                new_data = self.object.advance_payment_data or []
                if isinstance(new_data, str):
                    new_data = json.loads(new_data)
                new_ap_ids = {int(item.get('id')) for item in new_data if item.get('id')}
                
                added_ids = new_ap_ids - old_ap_ids
                if added_ids:
                    AdvancePaymentDetail.objects.filter(id__in=added_ids).update(is_billed=True)
                    
                removed_ids = old_ap_ids - new_ap_ids
                if removed_ids:
                    AdvancePaymentDetail.objects.filter(id__in=removed_ids).update(is_billed=False)
                    
                # Mutate JSON so UI shows correct state
                if new_data:
                    mutated = False
                    for item in new_data:
                        if not item.get('is_billed'):
                            item['is_billed'] = True
                            mutated = True
                    if mutated:
                        self.object.advance_payment_data = new_data
                        self.object.save(update_fields=['advance_payment_data'])
                        
            except Exception as e:
                import traceback
                traceback.print_exc()
                    
            # Handle AR Transfer and Voucher Generation if just posted
            if 'is_posted' in form.changed_data and form.cleaned_data['is_posted']:
                try:
                    # 1. AR Transfer (if not already transferred)
                    if not self.object.is_ar_transferred:
                        ReceivableTransferService.create_from_source(self.object)
                        self.object.is_ar_transferred = True
                    
                    # 2. Update Status to ISSUED
                    self.object.status = ClientBill.BillStatus.ISSUED
                    self.object.save(update_fields=['is_ar_transferred', 'status'])
                    
                    # 3. Voucher Generation
                    voucher = ReceivableTransferService.generate_voucher_for_bill(self.object, self.request.user)
                    if voucher:
                        messages.success(self.request, f"成功拋轉應收帳款並產生傳票 ({voucher.voucher_no})！")
                    else:
                        messages.success(self.request, "成功拋轉應收帳款，但無收費項目可產生傳票。")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    messages.error(self.request, f"拋轉失敗：{str(e)}")
                    # Revert is_posted flag on error
                    self.object.is_posted = False
                    self.object.save(update_fields=['is_posted'])
                    return redirect(self.get_success_url())

        if 'is_posted' not in form.changed_data or not form.cleaned_data['is_posted']:
            messages.success(self.request, f'帳單 {self.object.bill_no} 更新成功！')
            
        return redirect(self.get_success_url())


class ClientBillDeleteView(LoginRequiredMixin, DeleteView):
    model = ClientBill
    template_name = 'bookkeeping/billing/confirm_delete.html'
    success_url = reverse_lazy('bookkeeping:bill_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_deleted = True
        self.object.save()
        messages.success(self.request, '帳單已成功刪除。')
        return HttpResponseRedirect(self.get_success_url())


class GenerateBillPaymentLinkView(LoginRequiredMixin, View):
    """產生客戶帳單的第三方支付連結"""

    def post(self, request, pk):
        import random
        from modules.payment.models import PaymentTransaction

        bill = get_object_or_404(ClientBill, pk=pk, is_deleted=False)

        if not bill.total_amount or bill.total_amount <= 0:
            return JsonResponse({'error': '帳單金額為零，無法產生支付連結。'}, status=400)

        random_suffix = f"{random.randint(0, 9999):04d}"
        merchant_trade_no = f"{bill.bill_no}{random_suffix}"[:20]

        PaymentTransaction.objects.create(
            merchant_trade_no=merchant_trade_no,
            total_amount=int(bill.total_amount),
            trade_desc=f"帳單 {bill.bill_no}",
            item_name=f"記帳服務費 ({bill.client.name})"[:200],
            payment_type=PaymentTransaction.PaymentType.ECPAY,
            related_app='bookkeeping',
            related_model='ClientBill',
            related_id=str(bill.pk),
        )

        base_url = f"{request.scheme}://{request.get_host()}"
        pay_url = f"{base_url}/payment/bill/{merchant_trade_no}/"
        return JsonResponse({'url': pay_url})


class ClientBillTransferView(LoginRequiredMixin, View):
    """拋轉帳單至應收帳款"""

    def post(self, request, pk):
        bill = get_object_or_404(ClientBill, pk=pk, is_deleted=False)
        if bill.is_ar_transferred:
            messages.warning(request, '此帳單已經拋轉過了！')
            return redirect('bookkeeping:bill_list')

        try:
            receivable = ReceivableTransferService.create_from_source(bill)
            bill.is_ar_transferred = True
            bill.save(update_fields=['is_ar_transferred'])
            messages.success(
                request,
                f'帳單 {bill.bill_no} 已成功拋轉為應收帳款 {receivable.receivable_no}！'
            )
        except Exception as e:
            messages.error(request, f'拋轉失敗：{str(e)}')

        return redirect('bookkeeping:bill_list')
