from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from core.mixins import BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin
from ..models import BankTransferReport, Collection


class BankTransferReportListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    """客戶端銀行匯款回報的後台核對列表。預設顯示待核對。"""
    model = BankTransferReport
    template_name = 'bank_transfer_report/list.html'
    context_object_name = 'reports'
    paginate_by = 25
    default_filter = 'PENDING'
    search_fields = [
        'last_five_digits',
        'receivable__receivable_no',
        'receivable__company_name',
    ]
    filter_choices = {
        'PENDING':   {'status': BankTransferReport.Status.PENDING},
        'CONFIRMED': {'status': BankTransferReport.Status.CONFIRMED},
        'REJECTED':  {'status': BankTransferReport.Status.REJECTED},
    }

    def get_queryset(self):
        return super().get_queryset().select_related('receivable')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '銀行匯款回報'
        context['model_name'] = 'internal_accounting:bank_transfer_report'
        context['model_app_label'] = 'internal_accounting'
        context['count_all']       = context['filter_counts']['ALL']
        context['count_pending']   = context['filter_counts']['PENDING']
        context['count_confirmed'] = context['filter_counts']['CONFIRMED']
        context['count_rejected']  = context['filter_counts']['REJECTED']
        return context


@login_required
@require_POST
def confirm_transfer_report_view(request, pk):
    """確認一筆匯款回報：自動建立對應的銀行收款（Collection），並標記為已確認。"""
    report = get_object_or_404(BankTransferReport, pk=pk, is_deleted=False)

    if report.status != BankTransferReport.Status.PENDING:
        messages.error(request, '此筆回報已處理過，無法重複確認。')
        return HttpResponseRedirect(reverse_lazy('internal_accounting:bank_transfer_report_list'))

    with transaction.atomic():
        collection = Collection.objects.create(
            receivable=report.receivable,
            date=report.transfer_date,
            method='bank',
            amount=report.amount,
            remarks=f'客戶匯款回報核對（後五碼 {report.last_five_digits}）',
        )
        report.collection = collection
        report.status = BankTransferReport.Status.CONFIRMED
        report.save(update_fields=['collection', 'status', 'updated_at'])

    messages.success(
        request,
        f'已確認並建立收款 {collection.collection_no}，請至收款管理過帳。',
    )
    return HttpResponseRedirect(reverse_lazy('internal_accounting:bank_transfer_report_list'))


@login_required
@require_POST
def reject_transfer_report_view(request, pk):
    """標記一筆匯款回報為「不符」（核對銀行對帳單後查無此筆）。"""
    report = get_object_or_404(BankTransferReport, pk=pk, is_deleted=False)

    if report.status != BankTransferReport.Status.PENDING:
        messages.error(request, '此筆回報已處理過，無法再標記。')
        return HttpResponseRedirect(reverse_lazy('internal_accounting:bank_transfer_report_list'))

    report.status = BankTransferReport.Status.REJECTED
    report.save(update_fields=['status', 'updated_at'])
    messages.success(request, '已將該筆回報標記為不符。')
    return HttpResponseRedirect(reverse_lazy('internal_accounting:bank_transfer_report_list'))
