from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from modules.client_portal.mixins import ClientRequiredMixin
from modules.bookkeeping.models import TaxFilingPeriod

class PortalLoginView(LoginView):
    template_name = 'client_portal/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'EXTERNAL':
            return reverse_lazy('client_portal:dashboard')
        # If a non-external user tries to log in here, just send them away
        return reverse_lazy('dashboard')

class DashboardView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/dashboard.html'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Client profile existence is guaranteed by ClientRequiredMixin
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client
        
        # Get pending VAT periods that require client attention
        context['pending_vat_periods'] = TaxFilingPeriod.objects.filter(
            year_record__client=client,
            filing_status__in=['waiting', 'not_notified']
        ).order_by('-year_record__year', '-period_start_month')
        
        # Financial summary: sum of this year's sales amount (just an example calculation)
        import datetime
        current_year = datetime.datetime.now().year - 1911 # ROC Year
        periods_this_year = TaxFilingPeriod.objects.filter(
            year_record__client=client, year_record__year=current_year
        )
        context['total_sales_this_year'] = sum([p.sales_amount for p in periods_this_year])
        context['total_payable_this_year'] = sum([p.payable_tax for p in periods_this_year])
        
        return context

class DocumentCenterView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/document_center.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client
        
        # Determine selected year or default to latest
        all_periods = TaxFilingPeriod.objects.filter(year_record__client=client).order_by('-year_record__year', '-period_start_month')
        
        # Get distinct years
        available_years = sorted(list(set(p.year_record.year for p in all_periods)), reverse=True)
        context['available_years'] = available_years
        
        selected_year = self.request.GET.get('year')
        if not selected_year and available_years:
            selected_year = available_years[0]
        elif selected_year:
            try:
                selected_year = int(selected_year)
            except ValueError:
                selected_year = available_years[0] if available_years else None
            
        context['selected_year'] = selected_year
        
        if selected_year:
            context['vat_periods'] = all_periods.filter(year_record__year=selected_year)
        else:
            context['vat_periods'] = all_periods
        
        return context

class ShareholderManagementView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/shareholders.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.request.user.bookkeeping_client_profile
        return context

class FinancialAnalysisView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/financial_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.request.user.bookkeeping_client_profile
        return context

class IncomeDeclarationView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/income_declaration.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.request.user.bookkeeping_client_profile
        return context

class DividendDeclarationView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/dividend_declaration.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.request.user.bookkeeping_client_profile
        return context

class ServiceRemunerationView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/service_remuneration.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.request.user.bookkeeping_client_profile
        return context

class SettingsView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.request.user.bookkeeping_client_profile
        return context
