from django.views.generic import UpdateView
from core.mixins import BusinessRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
import math

from ..models import BookkeepingClient
from ..models.income_tax import ProvisionalTax, FilingStatus
from ..services.provisional_tax_notification import send_provisional_tax_notification


class ProvisionalTaxDetailView(BusinessRequiredMixin, UpdateView):
    """
    暫繳申報詳情頁：顯示並編輯單一暫繳申報的完整資料
    URL: /bookkeeping/income-tax/<client_pk>/provisional/<pk>/
    """
    model = ProvisionalTax
    template_name = 'bookkeeping/income_tax/provisional_tax_detail.html'
    fields = [
        'last_year_tax', 'provisional_amount', 'provisional_deadline',
        'filing_document',
        'is_filed', 'filing_date',
        'tax_deadline', 'payment_method',
        'filing_status',
        'notes',
    ]

    def get_object(self, queryset=None):
        return get_object_or_404(
            ProvisionalTax,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_success_url(self):
        return reverse('bookkeeping:provisional_tax_detail', kwargs={
            'client_pk': self.kwargs['client_pk'],
            'pk': self.object.pk,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provisional = self.object
        client = provisional.year_record.client

        # Initialize checklist if empty (for existing records)
        if not provisional.checklist:
            import copy
            from ..models.income_tax import DEFAULT_PROVISIONAL_CHECKLIST
            provisional.checklist = copy.deepcopy(DEFAULT_PROVISIONAL_CHECKLIST)
            provisional.save(update_fields=['checklist'])

        context['client'] = client
        context['provisional'] = provisional
        context['year_obj'] = provisional.year_record
        context['setting'] = getattr(client, 'income_tax_setting', None)
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'filing_document' in form.fields:
            form.fields['filing_document'].required = False
        return form

    def form_valid(self, form):
        provisional = form.save(commit=False)

        # Handle checklist from POST
        checklist = provisional.checklist or []
        for item in checklist:
            item['checked'] = self.request.POST.get(f"checklist_{item['key']}") == 'on'

        provisional.checklist = checklist

        # Auto-calculate provisional_amount from last_year_tax if not manually overridden
        last_year_tax = provisional.last_year_tax or 0
        calculated = math.floor(float(last_year_tax) * 0.5)
        if calculated <= 2000:
            calculated = 0

        # Only auto-set if user hasn't manually entered a different value
        submitted_amount = int(self.request.POST.get('provisional_amount', 0) or 0)
        if submitted_amount == 0 and last_year_tax > 0:
            provisional.provisional_amount = calculated

        # Auto-set payment_method and filing_status when amount is 0
        if provisional.provisional_amount == 0:
            provisional.payment_method = 'no_payment'
            provisional.filing_status = 'no_payment_needed'

        provisional.save()
        messages.success(self.request, '暫繳申報資料已儲存。')
        return super().form_valid(form)


class SendProvisionalTaxNotificationView(BusinessRequiredMixin, View):
    """
    POST: 發送暫繳申報繳稅通知給客戶（Line/Email）
    發送成功後將 filing_status 更新為 'waiting'
    """

    def post(self, request, client_pk, pk):
        provisional = get_object_or_404(
            ProvisionalTax,
            pk=pk,
            year_record__client__pk=client_pk,
        )

        results = send_provisional_tax_notification(provisional, request)

        if results['success_channels']:
            provisional.filing_status = FilingStatus.WAITING
            provisional.save(update_fields=['filing_status'])

        return JsonResponse({
            'success_channels': results['success_channels'],
            'error_channels': results['error_channels'],
        })
