from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin


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


