from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from core.mixins import ListActionMixin, PrevNextMixin
from ..models import EquityTransaction
from ..forms import EquityTransactionForm

class EquityTransactionListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = EquityTransaction
    template_name = 'equity_transaction/list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Organization Type Filter
        org_type = self.request.GET.get('org_type', 'ALL')
        if org_type in ['LTD', 'CORP']:
            queryset = queryset.filter(organization_type=org_type)
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(company_name__icontains=q) |
                Q(unified_business_no__icontains=q) |
                Q(shareholder_name__icontains=q)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_org_type'] = self.request.GET.get('org_type', 'ALL')
        return context

class EquityTransactionCreateView(LoginRequiredMixin, CreateView):
    model = EquityTransaction
    form_class = EquityTransactionForm
    template_name = 'equity_transaction/form.html'
    
    def get_success_url(self):
        if self.object.shareholder_register:
            return reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.shareholder_register.pk})
        return reverse_lazy('registration:equity_transaction_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        if 'register_id' in self.request.GET:
            context['register_id'] = self.request.GET['register_id']
            from ..models import ShareholderRegister
            try:
                context['shareholder_register'] = ShareholderRegister.objects.get(pk=context['register_id'])
            except ShareholderRegister.DoesNotExist:
                pass
        # Calculate Cancel URL
        if 'register_id' in self.request.GET:
            context['cancel_url'] = reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.request.GET['register_id']})
        else:
            context['cancel_url'] = reverse_lazy('registration:equity_transaction_list')
            
        return context

    def form_valid(self, form):
        register_id = self.request.GET.get('register_id')
        if register_id:
            form.instance.shareholder_register_id = register_id
        return super().form_valid(form)

class EquityTransactionUpdateView(LoginRequiredMixin, PrevNextMixin, UpdateView):
    model = EquityTransaction
    form_class = EquityTransactionForm
    template_name = 'equity_transaction/form.html'
    
    def get_success_url(self):
        if self.object.shareholder_register:
            return reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.shareholder_register.pk})
        return reverse_lazy('registration:equity_transaction_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'update'
        if self.object.shareholder_register:
            context['shareholder_register'] = self.object.shareholder_register
        # Calculate Cancel URL
        if self.object.shareholder_register:
            context['cancel_url'] = reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.shareholder_register.pk})
        else:
            context['cancel_url'] = reverse_lazy('registration:equity_transaction_list')
        return context

class EquityTransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = EquityTransaction
    template_name = 'equity_transaction/confirm_delete.html'
    
    def get_success_url(self):
        if self.object.shareholder_register:
            return reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.shareholder_register.pk})
        return reverse_lazy('registration:equity_transaction_list')

from django.views.generic import TemplateView
class TestRenderView(TemplateView):
    template_name = 'test_render.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test_variable'] = 'HELLO WORLD'
        return context
