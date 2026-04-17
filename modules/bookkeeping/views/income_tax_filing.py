import json
from core.mixins import BusinessRequiredMixin
import copy
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import UpdateView

from ..models.income_tax import IncomeTaxFiling, DEFAULT_INCOME_TAX_CHECKLIST

DEFAULT_RECONCILIATION = [
    {'key': 'salary', 'label': '薪資', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'profession', 'label': '執行業務', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'interest', 'label': '利息', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'rental', 'label': '租賃', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'royalty', 'label': '權利金', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'dividend', 'label': '股利或盈餘', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'lottery', 'label': '機會中獎', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'retirement_income', 'label': '退職所得', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
    {'key': 'other_income', 'label': '其他', 'declared': 0, 'minus_prev_payable': 0, 'plus_prev_prepaid': 0, 'plus_curr_payable': 0, 'minus_curr_prepaid': 0, 'retirement': 0, 'other': 0, 'book_amount': 0, 'tax_withheld': 0, 'difference': 0, 'remark': ''},
]


class IncomeTaxFilingDetailView(BusinessRequiredMixin, UpdateView):
    model = IncomeTaxFiling
    fields = [
        'annual_tax', 'provisional_credit', 'withholding_credit',
        'self_pay_amount', 'undistributed_earnings', 'undistributed_surtax',
        'total_payable', 'notes',
    ]
    template_name = 'bookkeeping/income_tax/income_tax_filing_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            IncomeTaxFiling,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_success_url(self):
        return reverse('bookkeeping:income_tax_filing_detail', kwargs={
            'client_pk': self.kwargs['client_pk'],
            'pk': self.object.pk,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filing = self.object
        client = filing.year_record.client
        context['client'] = client
        context['filing'] = filing
        context['year_obj'] = filing.year_record
        context['setting'] = getattr(client, 'income_tax_setting', None)

        # Ensure checklist is a list (upgrade old dict format)
        checklist = filing.checklist
        if not checklist or isinstance(checklist, dict):
            checklist = copy.deepcopy(DEFAULT_INCOME_TAX_CHECKLIST)
        context['checklist_json'] = json.dumps(checklist, ensure_ascii=False)

        # Sibling data for "帶入資料" button
        sibling = {}
        try:
            prov = filing.year_record.provisional_tax
            sibling['provisionalCredit'] = float(prov.provisional_amount)
        except Exception:
            sibling['provisionalCredit'] = 0
        try:
            div = filing.year_record.dividend_tax
            # 未分配金額 = distributable_amount - distributed_amount
            undist = float(div.distributable_amount) - float(div.distributed_amount)
            sibling['undistributedEarnings'] = max(undist, 0)
            sibling['undistributedSurtax'] = float(div.undistributed_surtax)
        except Exception:
            sibling['undistributedEarnings'] = 0
            sibling['undistributedSurtax'] = 0
        context['sibling_json'] = json.dumps(sibling, ensure_ascii=False)

        # Reconciliation data
        recon = filing.reconciliation
        if not recon or not isinstance(recon, list):
            recon = copy.deepcopy(DEFAULT_RECONCILIATION)
        context['reconciliation_json'] = json.dumps(recon, ensure_ascii=False)

        # Slide-over panel: 媒體檔查閱資料
        current_year = filing.year_record.year
        context['slideover_api_url'] = reverse(
            'bookkeeping:api_income_tax_media_data',
            kwargs={'client_pk': client.pk},
        )
        context['slideover_current_year'] = current_year
        context['slideover_prior_year'] = current_year - 1

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.required = False
        return form

    def form_valid(self, form):
        filing = form.save(commit=False)

        # Parse numeric fields
        for field_name in ['annual_tax', 'provisional_credit', 'withholding_credit',
                           'self_pay_amount', 'undistributed_earnings',
                           'undistributed_surtax', 'total_payable']:
            val = self.request.POST.get(field_name, '0')
            try:
                setattr(filing, field_name, int(val) if val else 0)
            except (ValueError, TypeError):
                setattr(filing, field_name, 0)

        # Filing status fields
        filing.payment_method = self.request.POST.get('payment_method', filing.payment_method)
        filing.filing_status = self.request.POST.get('filing_status', filing.filing_status)
        filing.is_filed = self.request.POST.get('is_filed') == 'on'
        filing.notes = self.request.POST.get('notes', '')

        # File uploads
        if 'filing_document' in self.request.FILES:
            filing.filing_document = self.request.FILES['filing_document']
        if 'media_file' in self.request.FILES:
            filing.media_file = self.request.FILES['media_file']

        # Save checklist from POST
        checklist_data = self.request.POST.get('checklist_json', '[]')
        try:
            filing.checklist = json.loads(checklist_data)
        except (json.JSONDecodeError, TypeError):
            pass

        # Save reconciliation from POST
        recon_data = self.request.POST.get('reconciliation_json', '[]')
        try:
            filing.reconciliation = json.loads(recon_data)
        except (json.JSONDecodeError, TypeError):
            pass

        filing.save()
        messages.success(self.request, '所得稅申報資料已儲存。')
        return super().form_valid(form)
