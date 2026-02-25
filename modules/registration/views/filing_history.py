from django.urls import reverse_lazy
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from core.mixins import PrevNextMixin
from ..models import FilingHistory
from ..forms import FilingHistoryForm

class FilingHistoryUpdateView(LoginRequiredMixin, PrevNextMixin, UpdateView):
    model = FilingHistory
    fields = ['year', 'category', 'filing_date', 'registration_no', 'is_completed']
    template_name = 'filing_history/form.html'
    prev_next_order_field = 'id'
    
    def get_success_url(self):
        # Redirect back to the parent CompanyFiling edit page or progress list
        return reverse_lazy('registration:company_filing_edit', kwargs={'pk': self.object.company_filing.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯申報明細'
        context['parent'] = self.object.company_filing
        return context

class FilingHistoryDeleteView(LoginRequiredMixin, DeleteView):
    model = FilingHistory
    template_name = 'filing_history/confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('registration:company_filing_edit', kwargs={'pk': self.object.company_filing.pk})
