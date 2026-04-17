from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.mixins import BusinessRequiredMixin, ListActionMixin, PrevNextMixin, FilterMixin, SearchMixin, SoftDeleteMixin, SortMixin
from django.contrib import messages
from ..models import Shareholder
from ..forms import ShareholderForm

class ShareholderListView(SortMixin, FilterMixin, SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    model = Shareholder
    template_name = 'shareholder/list.html'
    context_object_name = 'shareholders'
    paginate_by = 25
    search_fields = ['name', 'id_number']
    default_filter = 'ACTIVE'
    filter_choices = {
        'ACTIVE':   {'is_active': True},
        'INACTIVE': {'is_active': False},
    }
    allowed_sort_fields = ['name', 'id_number', 'nationality', 'birthday', 'is_active']
    default_sort = ['name']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_all']      = context['filter_counts']['ALL']
        context['count_active']   = context['filter_counts']['ACTIVE']
        context['count_inactive'] = context['filter_counts']['INACTIVE']
        return context

class ShareholderCreateView(BusinessRequiredMixin, CreateView):
    model = Shareholder
    form_class = ShareholderForm
    template_name = 'shareholder/form.html'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:shareholder_update', kwargs={'pk': self.object.pk})

class ShareholderUpdateView(BusinessRequiredMixin, PrevNextMixin, UpdateView):
    model = Shareholder
    form_class = ShareholderForm
    template_name = 'shareholder/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:shareholder_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

class ShareholderDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = Shareholder
    template_name = 'shareholder/confirm_delete.html'
    success_url = reverse_lazy('registration:shareholder_list')
