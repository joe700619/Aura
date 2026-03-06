from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse

from ..models import TaxFilingPeriod, BookkeepingClient


class TaxFilingPeriodDetailView(LoginRequiredMixin, UpdateView):
    """
    期別詳情頁：顯示並編輯單一期的完整申報資料
    URL: /bookkeeping/business-tax/<client_pk>/period/<pk>/
    """
    model = TaxFilingPeriod
    template_name = 'bookkeeping/business_tax/period_detail.html'
    fields = [
        'invoice_received_date', 'sales_amount', 'tax_amount', 'input_amount', 'input_tax',
        'retained_tax', 'payable_tax',
        'filing_document', 'media_file',
        'is_filed', 'filing_date',
        'tax_deadline', 'period_payment_method',
        'filing_status', 'reply_time', 'reply_method',
    ]

    def get_object(self, queryset=None):
        return get_object_or_404(
            TaxFilingPeriod,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_success_url(self):
        client_pk = self.kwargs['client_pk']
        year = self.object.year_record.year
        return (
            reverse('bookkeeping:business_tax_detail', kwargs={'pk': client_pk})
            + f'?year={year}'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.object
        client = period.year_record.client
        context['client'] = client
        context['period'] = period
        context['year_obj'] = period.year_record
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Make file fields optional on re-submit (don't require re-upload if already set)
        for fname in ('filing_document', 'media_file'):
            if fname in form.fields:
                form.fields[fname].required = False
        return form
