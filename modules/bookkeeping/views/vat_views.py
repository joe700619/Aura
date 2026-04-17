"""
Views for VAT notification sending and public payment confirmation callback.
"""
from django.views import View
from core.mixins import BusinessRequiredMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone

from ..models import TaxFilingPeriod, BookkeepingClient, ClientBill
from modules.internal_accounting.models.receivable import Receivable
from ..services.vat_notification import send_vat_notification


class SendVATNotificationView(BusinessRequiredMixin, View):
    """
    POST: send Line/Email notification to the client for a specific period.
    Updates filing_status → 'waiting'.
    """

    def post(self, request, client_pk, pk):
        period = get_object_or_404(
            TaxFilingPeriod,
            pk=pk,
            year_record__client__pk=client_pk,
        )

        results = send_vat_notification(period, request)

        if results['success_channels']:
            period.filing_status = TaxFilingPeriod.FilingStatus.WAITING
            period.save(update_fields=['filing_status'])
            success_list = '、'.join(results['success_channels'])
            messages.success(request, f'已透過 {success_list} 發送通知，等待客戶回覆。')
        
        if results['error_channels']:
            err_list = '、'.join(results['error_channels'])
            messages.warning(request, f'以下管道發送失敗或設定不完整：{err_list}')

        from django.urls import reverse
        return redirect(
            reverse('bookkeeping:business_tax_period_detail',
                    kwargs={'client_pk': client_pk, 'pk': pk})
        )


class VATConfirmView(View):
    """
    Public (no login) callback page.
    Client clicks link in notification → confirms payment here.
    """

    def get(self, request, token):
        period = get_object_or_404(TaxFilingPeriod, confirm_token=token)
        client = period.year_record.client
        context = {
            'period': period,
            'client': client,
            'already_confirmed': period.filing_status == TaxFilingPeriod.FilingStatus.PAID,
        }
        return render(request, 'bookkeeping/business_tax/vat_confirm.html', context)

    def post(self, request, token):
        period = get_object_or_404(TaxFilingPeriod, confirm_token=token)

        if period.filing_status != TaxFilingPeriod.FilingStatus.PAID:
            period.filing_status = TaxFilingPeriod.FilingStatus.PAID
            period.reply_time = timezone.now()
            period.reply_method = TaxFilingPeriod.ReplyMethod.AUTO
            period.save(update_fields=['filing_status', 'reply_time', 'reply_method'])

        return render(request, 'bookkeeping/business_tax/vat_confirm_done.html', {
            'period': period,
            'client': period.year_record.client,
        })


class CheckOutstandingReceivablesAPI(BusinessRequiredMixin, View):
    """
    API endpoint to check if a client has any unposted bills, and if not,
    fetch all their outstanding receivables.
    """

    def get(self, request, client_pk):
        client = get_object_or_404(BookkeepingClient, pk=client_pk)

        # 1. 檢查是否有未拋轉至應收的帳單
        unposted_bills = ClientBill.objects.filter(
            client=client,
            is_posted=False
        ).exclude(status='void')

        if unposted_bills.exists():
            return JsonResponse({
                'has_unposted_bills': True,
                'bills_count': unposted_bills.count()
            })

        # 2. 如果沒有，透過統編查詢未結清的應收帳款
        receivables_data = []
        total_outstanding = 0

        if client.tax_id:
            receivables = Receivable.objects.filter(
                unified_business_no=client.tax_id
            )
            for r in receivables:
                outstanding = r.outstanding_balance
                if outstanding > 0:
                    receivables_data.append({
                        'id': r.pk,
                        'receivable_no': r.receivable_no,
                        'date': r.created_at.strftime('%Y-%m-%d') if r.created_at else '',
                        'total_amount': float(r.total_amount),
                        'outstanding_balance': float(outstanding)
                    })
                    total_outstanding += outstanding

        return JsonResponse({
            'has_unposted_bills': False,
            'receivables': receivables_data,
            'total_outstanding': float(total_outstanding)
        })

