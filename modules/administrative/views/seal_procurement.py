from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.db import transaction
from django.db.models import Sum
from django.contrib import messages
from django.utils import timezone
from core.mixins import BusinessRequiredMixin, CopyMixin, PrevNextMixin, ListActionMixin, SearchMixin, SoftDeleteMixin, FilterMixin
from ..models import SealProcurement
from ..forms import SealProcurementForm, SealProcurementItemFormSet


FIRM_NAME = '勤信聯合會計師事務所'
FIRM_TAX_ID = '82530323'


def _transfer_seal_to_advance_payment(procurement, user):
    """Create an AdvancePayment with one AdvancePaymentDetail per purchase item."""
    from ..models.advance_payment import AdvancePayment, AdvancePaymentDetail

    purchase_items = procurement.items.filter(movement_type='purchase')
    total = purchase_items.aggregate(total=Sum('subtotal'))['total'] or 0

    today = timezone.now().date()
    count = AdvancePayment.objects.filter(date=today).count() + 1
    advance_no = f'AP-{today.strftime("%Y%m%d")}-{count:03d}'

    ap = AdvancePayment.objects.create(
        advance_no=advance_no,
        date=today,
        applicant=user,
        total_amount=total,
        description=f'印章採購代墊 - {procurement.company_name}（統編：{procurement.unified_business_no}）',
    )

    for item in purchase_items:
        if item.is_absorbed_by_customer:
            company = procurement.company_name
            tax_id = procurement.unified_business_no
        else:
            company = FIRM_NAME
            tax_id = FIRM_TAX_ID

        AdvancePaymentDetail.objects.create(
            advance_payment=ap,
            is_customer_absorbed=item.is_absorbed_by_customer,
            unified_business_no=tax_id,
            reason=f'印章採購 - {company} - {item.get_seal_type_display()}',
            amount=item.subtotal,
            payment_type=AdvancePaymentDetail.PaymentType.SEAL,
        )

    return ap


class SealProcurementListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = SealProcurement
    template_name = 'administrative/seal_procurement/list.html'
    context_object_name = 'items'
    paginate_by = 25
    search_fields = ['company_name', 'unified_business_no', 'main_contact']
    filter_choices = {
        'inventory':    {'transfer_to_inventory': True},
        'no_inventory': {'transfer_to_inventory': False},
    }

    def get_base_queryset(self):
        return super().get_base_queryset()

    def _base_qs_for_counts(self):
        return self.model.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '印章採購管理'
        return context


class SealProcurementCreateView(CopyMixin, BusinessRequiredMixin, CreateView):
    model = SealProcurement
    form_class = SealProcurementForm
    template_name = 'administrative/seal_procurement/form.html'

    def get_success_url(self):
        return reverse_lazy('administrative:seal_procurement_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增印章採購單'
        if self.request.POST:
            context['formset'] = SealProcurementItemFormSet(self.request.POST)
        else:
            context['formset'] = SealProcurementItemFormSet()
        return context

    def form_valid(self, form):
        formset = SealProcurementItemFormSet(self.request.POST)
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            self.object.recalculate_subtotal()
            messages.success(self.request, '印章採購單已建立。')

        if self.object.transfer_to_advance and not self.object.is_advance_transferred:
            try:
                with transaction.atomic():
                    ap = _transfer_seal_to_advance_payment(self.object, self.request.user)
                    self.object.is_advance_transferred = True
                    self.object.save(update_fields=['is_advance_transferred'])
                messages.success(self.request, f'已成功建立代墊款單：{ap.advance_no}（金額：${self.object.seal_cost_subtotal:,}）')
            except Exception as e:
                messages.error(self.request, f'建立代墊款失敗：{str(e)}')

        return redirect(self.get_success_url())


class SealProcurementUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = SealProcurement
    form_class = SealProcurementForm
    template_name = 'administrative/seal_procurement/form.html'

    def get_success_url(self):
        return reverse_lazy('administrative:seal_procurement_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯印章採購單 - {self.object.company_name}'
        if self.request.POST:
            context['formset'] = SealProcurementItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = SealProcurementItemFormSet(instance=self.object)
        if self.request.method == 'GET' and hasattr(self.object, 'history'):
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
        was_transferred = self.object.is_advance_transferred
        formset = SealProcurementItemFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            formset.save()
            self.object.recalculate_subtotal()
            messages.success(self.request, '印章採購單已更新。')

        if self.object.transfer_to_advance and not was_transferred:
            try:
                with transaction.atomic():
                    ap = _transfer_seal_to_advance_payment(self.object, self.request.user)
                    self.object.is_advance_transferred = True
                    self.object.save(update_fields=['is_advance_transferred'])
                messages.success(self.request, f'已成功建立代墊款單：{ap.advance_no}（金額：${self.object.seal_cost_subtotal:,}）')
            except Exception as e:
                messages.error(self.request, f'建立代墊款失敗：{str(e)}')

        return redirect('administrative:seal_procurement_update', pk=self.object.pk)


class SealProcurementDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = SealProcurement
    template_name = 'administrative/seal_procurement/confirm_delete.html'
    success_url = reverse_lazy('administrative:seal_procurement_list')
