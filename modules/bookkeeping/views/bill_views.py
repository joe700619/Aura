from datetime import date, datetime, timedelta
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.db import models as db_models
from django.db import transaction
from django.forms import ModelForm, HiddenInput
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from core.mixins import BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin, PrevNextMixin, SoftDeleteMixin
from ..models import BookkeepingClient, ClientBill
from modules.administrative.models import AdvancePaymentDetail
from modules.internal_accounting.services import ReceivableTransferService

# ── 批次產帳輔助常數 ──────────────────────────────────────────────
# 各收費週期對應的發單月份
_BILLING_MONTHS = {
    'monthly':              list(range(1, 13)),
    'bimonthly':            [1, 3, 5, 7, 9, 11],
    'bimonthly_auto':       [1, 3, 5, 7, 9, 11],
    'semi_annual':          [6, 12],
    'semi_annual_prepaid':  [6, 12],
    'annual':               [1],
}
# 各收費週期的年度發單月（加帳簿費的月份）
_ANNUAL_BILL_MONTH = {
    'monthly':              5,
    'bimonthly':            5,
    'bimonthly_auto':       5,
    'semi_annual':          6,
    'semi_annual_prepaid':  6,
    'annual':               1,
}
# 各收費週期對應的數量（計算服務費時用）
_CYCLE_QTY = {
    'monthly':              1,
    'bimonthly':            2,
    'bimonthly_auto':       2,
    'semi_annual':          3,
    'semi_annual_prepaid':  6,
    'annual':               12,
}


def _get_clients_for_batch(month):
    """
    回傳本月應開帳單的客戶清單（list of dict）。
    Step 1: 依 billing_cycle 判斷本月是否發單。
    Step 2: 判斷是否為年度發單月。
    """
    clients = (
        BookkeepingClient.objects
        .filter(is_deleted=False, billing_status='billing')
        .prefetch_related('service_fees')
        .select_related('bookkeeping_assistant')
        .order_by('name')
    )
    today = date.today()
    result = []
    for client in clients:
        active_fee = (
            client.service_fees
            .filter(
                db_models.Q(end_date__isnull=True) | db_models.Q(end_date__gte=today)
            )
            .order_by('-effective_date')
            .first()
        )
        if not active_fee:
            continue
        cycle = active_fee.billing_cycle
        if month not in _BILLING_MONTHS.get(cycle, []):
            continue
        result.append({
            'client':     client,
            'active_fee': active_fee,
            'is_annual':  (_ANNUAL_BILL_MONTH.get(cycle) == month),
        })
    return result


def _build_quotation_data(active_fee, year, month, is_annual):
    """依服務費資料組建 quotation_data（list of row dicts）。"""
    qty          = _CYCLE_QTY.get(active_fee.billing_cycle, 1)
    service_fee  = active_fee.service_fee
    ledger_fee   = active_fee.ledger_fee
    service_amt  = service_fee * qty + (service_fee if is_annual else 0)
    remark = (
        f'{year}年{month}月會計費用及年度所得稅申報'
        if is_annual else
        f'{year}年{month}月會計服務費用'
    )
    rows = [{
        'service_code': '',
        'service_name': '2.1會計服務費',
        'amount': service_amt,
        'remark': remark,
        'is_company_law_22_1': False,
        'is_money_laundering_check': False,
        'is_business_entity_change': False,
        'is_shareholder_list_change': False,
    }]
    if is_annual and ledger_fee > 0:
        rows.append({
            'service_code': '',
            'service_name': '2.2帳簿費',
            'amount': ledger_fee,
            'remark': f'{year}年{month}月帳簿費',
            'is_company_law_22_1': False,
            'is_money_laundering_check': False,
            'is_business_entity_change': False,
            'is_shareholder_list_change': False,
        })
    return rows


class BookkeepingClientSearchView(BusinessRequiredMixin, View):
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
                'billing_cycle': active_fee.billing_cycle if active_fee else '',
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


class FetchUnbilledAdvancePaymentsView(BusinessRequiredMixin, View):
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


class BillBatchPreviewView(BusinessRequiredMixin, View):
    """
    AJAX: 預覽本月將產生的帳單清單（不實際建立）。
    POST params: year, month, annual_override ('yes'|'no'|'')
    """
    def post(self, request):
        try:
            year  = int(request.POST.get('year', 0))
            month = int(request.POST.get('month', 0))
        except (ValueError, TypeError):
            return JsonResponse({'error': '無效的年度或月份'}, status=400)
        if not (1 <= month <= 12) or not year:
            return JsonResponse({'error': '月份必須介於 1-12'}, status=400)

        annual_override = request.POST.get('annual_override', '')
        candidates = _get_clients_for_batch(month)
        if annual_override == 'yes':
            for c in candidates: c['is_annual'] = True
        elif annual_override == 'no':
            for c in candidates: c['is_annual'] = False

        existing = set(
            ClientBill.objects.filter(year=year, month=month)
            .values_list('client_id', flat=True)
        )

        items = []
        for c in candidates:
            active_fee = c['active_fee']
            is_annual  = c['is_annual']
            rows       = _build_quotation_data(active_fee, year, month, is_annual)
            total      = sum(r['amount'] for r in rows)
            items.append({
                'client_id':      c['client'].pk,
                'client_name':    c['client'].name,
                'tax_id':         c['client'].tax_id or '',
                'billing_cycle':  active_fee.get_billing_cycle_display(),
                'is_annual':      is_annual,
                'service_fee':    active_fee.service_fee,
                'ledger_fee':     active_fee.ledger_fee if is_annual else 0,
                'total':          total,
                'already_exists': c['client'].pk in existing,
            })

        return JsonResponse({
            'items':      items,
            'new_count':  sum(1 for i in items if not i['already_exists']),
            'skip_count': sum(1 for i in items if i['already_exists']),
        })


class BillBatchGenerateView(BusinessRequiredMixin, View):
    """
    POST: 批次建立帳單（已存在的跳過）。
    POST params: year, month, bill_date, due_date, annual_override
    """
    def post(self, request):
        try:
            year  = int(request.POST.get('year', 0))
            month = int(request.POST.get('month', 0))
        except (ValueError, TypeError):
            return JsonResponse({'error': '無效的年度或月份'}, status=400)
        if not (1 <= month <= 12) or not year:
            return JsonResponse({'error': '月份必須介於 1-12'}, status=400)

        try:
            bill_date_str = request.POST.get('bill_date', '')
            due_date_str  = request.POST.get('due_date', '')
            bill_date = (
                datetime.strptime(bill_date_str, '%Y-%m-%d').date()
                if bill_date_str else date.today()
            )
            due_date = (
                datetime.strptime(due_date_str, '%Y-%m-%d').date()
                if due_date_str else date.today() + timedelta(days=30)
            )
        except ValueError:
            return JsonResponse({'error': '無效的日期格式'}, status=400)

        annual_override = request.POST.get('annual_override', '')
        candidates = _get_clients_for_batch(month)
        if annual_override == 'yes':
            for c in candidates: c['is_annual'] = True
        elif annual_override == 'no':
            for c in candidates: c['is_annual'] = False

        created_count = skipped_count = 0
        with transaction.atomic():
            for c in candidates:
                active_fee     = c['active_fee']
                is_annual      = c['is_annual']
                quotation_data = _build_quotation_data(active_fee, year, month, is_annual)
                total          = sum(r['amount'] for r in quotation_data)

                _, created = ClientBill.objects.get_or_create(
                    client=c['client'],
                    year=year,
                    month=month,
                    defaults={
                        'bill_date':      bill_date,
                        'due_date':       due_date,
                        'status':         ClientBill.BillStatus.DRAFT,
                        'quotation_data': quotation_data,
                        'cost_sharing_data': c['client'].cost_sharing_data or [],
                        'total_amount':   total,
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        return JsonResponse({
            'success':  True,
            'created':  created_count,
            'skipped':  skipped_count,
            'message':  f'批次產帳完成：新建 {created_count} 筆，跳過 {skipped_count} 筆（已存在）',
        })


class ClientBillListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = ClientBill
    template_name = 'bookkeeping/billing/list.html'
    context_object_name = 'bills'
    create_button_label = '新增帳單'
    paginate_by = 25
    default_filter = 'draft'
    search_fields = ['bill_no', 'client__name', 'client__tax_id']
    filter_choices = {
        'draft':   {'status': 'draft'},
        'issued':  {'status': 'issued'},
        'paid':    {'status': 'paid'},
        'overdue': {'status': 'overdue'},
        'void':    {'status': 'void'},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().filter(
            is_deleted=False
        ).select_related('client')

    def _base_qs_for_counts(self):
        return ClientBill.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['custom_create_url'] = reverse_lazy('bookkeeping:bill_create')
        fc = context['filter_counts']
        context['count_draft']   = fc['draft']
        context['count_issued']  = fc['issued']
        context['count_paid']    = fc['paid']
        context['count_overdue'] = fc['overdue']
        context['count_void']    = fc['void']
        from django.urls import reverse
        context['today']                  = date.today()
        context['today_str']              = date.today().strftime('%Y-%m-%d')
        context['due_date_default_str']   = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
        context['bill_batch_preview_url'] = reverse('bookkeeping:bill_batch_preview')
        context['bill_batch_generate_url'] = reverse('bookkeeping:bill_batch_generate')
        return context


class ClientBillCreateView(BusinessRequiredMixin, CreateView):
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


class ClientBillUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = ClientBill
    form_class = ClientBillForm
    template_name = 'bookkeeping/billing/form.html'
    success_url = reverse_lazy('bookkeeping:bill_list')

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ClientBill.BillStatus.choices
        context['line_requires_posting'] = True
        if self.object and hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list
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

                    # 4. 自動產生第三方支付連結（若金額 > 0 且尚未建立）
                    if self.object.total_amount and self.object.total_amount > 0:
                        try:
                            import random
                            from modules.payment.models import PaymentTransaction
                            already_exists = PaymentTransaction.objects.filter(
                                related_app='bookkeeping',
                                related_model='ClientBill',
                                related_id=str(self.object.pk),
                            ).exists()
                            if not already_exists:
                                random_suffix = f"{random.randint(0, 9999):04d}"
                                merchant_trade_no = f"{self.object.bill_no}{random_suffix}"[:20]
                                PaymentTransaction.objects.create(
                                    merchant_trade_no=merchant_trade_no,
                                    total_amount=int(self.object.total_amount),
                                    trade_desc=f"帳單 {self.object.bill_no}",
                                    item_name=f"記帳服務費 ({self.object.client.name})"[:200],
                                    payment_type=PaymentTransaction.PaymentType.ECPAY,
                                    related_app='bookkeeping',
                                    related_model='ClientBill',
                                    related_id=str(self.object.pk),
                                )
                        except Exception:
                            pass  # 支付連結產生失敗不影響主流程
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


class ClientBillDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = ClientBill
    template_name = 'bookkeeping/billing/confirm_delete.html'
    success_url = reverse_lazy('bookkeeping:bill_list')


class GenerateBillPaymentLinkView(BusinessRequiredMixin, View):
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


class ClientBillTransferView(BusinessRequiredMixin, View):
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
