from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.mixins import BusinessRequiredMixin, ListActionMixin, PrevNextMixin, FilterMixin, SearchMixin, SoftDeleteMixin, SortMixin
from ..models import EquityTransaction
from ..forms import EquityTransactionForm

class EquityTransactionListView(SortMixin, FilterMixin, SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    model = EquityTransaction
    template_name = 'equity_transaction/list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    search_fields = ['shareholder_name', 'shareholder_register__company_name', 'shareholder_register__unified_business_no', 'registration_no']
    filter_choices = {
        'LTD':  {'organization_type': 'LTD'},
        'CORP': {'organization_type': 'CORP'},
    }
    allowed_sort_fields = ['registration_no', 'transaction_date', 'shareholder_name', 'transaction_reason', 'stock_type', 'share_count', 'unit_price', 'total_amount', 'is_completed']
    default_sort = ['-transaction_date']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_all']  = context['filter_counts']['ALL']
        context['count_ltd']  = context['filter_counts']['LTD']
        context['count_corp'] = context['filter_counts']['CORP']
        return context

class EquityTransactionCreateView(BusinessRequiredMixin, CreateView):
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

class EquityTransactionUpdateView(BusinessRequiredMixin, PrevNextMixin, UpdateView):
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

        # 編修紀錄
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list

        return context

class EquityTransactionDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = EquityTransaction
    template_name = 'equity_transaction/confirm_delete.html'
    
    def get_success_url(self):
        if self.object.shareholder_register:
            return reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.shareholder_register.pk})
        return reverse_lazy('registration:equity_transaction_list')

