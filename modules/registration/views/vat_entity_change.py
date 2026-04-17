from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, SortMixin, PrevNextMixin, SoftDeleteMixin
from ..models import VATEntityChange
from ..forms import VATEntityChangeForm


class VATEntityChangeListView(SortMixin, SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    model = VATEntityChange
    template_name = 'vat_entity_change/list.html'
    context_object_name = 'items'
    paginate_by = 25
    search_fields = ['company_name', 'unified_business_no', 'registration_no', 'assistant_name']
    allowed_sort_fields = ['company_name', 'unified_business_no', 'registration_no', 'assistant_name', 'is_completed', 'created_at', 'closed_at']
    default_sort = ['-created_at']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class VATEntityChangeCreateView(BusinessRequiredMixin, CreateView):
    model = VATEntityChange
    form_class = VATEntityChangeForm
    template_name = 'vat_entity_change/form.html'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:vat_entity_change_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增營業人變更登記'
        context['action'] = 'create'
        return context


class VATEntityChangeUpdateView(BusinessRequiredMixin, PrevNextMixin, UpdateView):
    model = VATEntityChange
    form_class = VATEntityChangeForm
    template_name = 'vat_entity_change/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:vat_entity_change_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯營業人變更登記'
        context['action'] = 'update'
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


class VATEntityChangeDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = VATEntityChange
    template_name = 'vat_entity_change/confirm_delete.html'
    success_url = reverse_lazy('registration:vat_entity_change_list')
