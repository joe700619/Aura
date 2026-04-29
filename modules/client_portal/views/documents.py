from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin
from modules.bookkeeping.models import TaxFilingPeriod, IncomeTaxYear, BusinessRegistrationDocument


class DocumentCenterView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/document_center.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client

        # ── 營業稅申報期別 ──
        all_periods = TaxFilingPeriod.objects.filter(
            year_record__client=client
        ).select_related('year_record').order_by('-year_record__year', '-period_start_month')

        # ── 所得稅年度 ──
        all_income_tax_years = IncomeTaxYear.objects.filter(
            client=client
        ).select_related('income_tax_filing').order_by('-year')

        # ── 合併兩者的年度供下拉選單使用 ──
        vat_years = set(p.year_record.year for p in all_periods)
        income_years = set(y.year for y in all_income_tax_years)
        available_years = sorted(vat_years | income_years, reverse=True)
        context['available_years'] = available_years

        # ── 處理年度篩選 ──
        selected_year = self.request.GET.get('year')
        if not selected_year and available_years:
            selected_year = available_years[0]
        elif selected_year:
            try:
                selected_year = int(selected_year)
            except ValueError:
                selected_year = available_years[0] if available_years else None

        context['selected_year'] = selected_year

        # ── 依年度篩選兩個資料集 ──
        if selected_year:
            context['vat_periods'] = all_periods.filter(year_record__year=selected_year)
            context['income_tax_years'] = all_income_tax_years.filter(year=selected_year)
        else:
            context['vat_periods'] = all_periods
            context['income_tax_years'] = all_income_tax_years

        # ── 商工登記文件（不分年度，全部顯示）──
        context['business_registration_documents'] = BusinessRegistrationDocument.objects.filter(
            registration__client=client,
            is_deleted=False,
        ).order_by('-document_date', '-created_at')
        return context
