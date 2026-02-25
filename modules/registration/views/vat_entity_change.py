from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import VATEntityChange
from ..forms import VATEntityChangeForm

class VATEntityChangeListView(LoginRequiredMixin, ListView):
    model = VATEntityChange
    template_name = 'vat_entity_change/list.html'
    context_object_name = 'items'

class VATEntityChangeCreateView(LoginRequiredMixin, CreateView):
    model = VATEntityChange
    form_class = VATEntityChangeForm
    template_name = 'vat_entity_change/form.html'
    success_url = reverse_lazy('registration:vat_entity_change_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增營業人變更登記'
        return context

class VATEntityChangeUpdateView(LoginRequiredMixin, UpdateView):
    model = VATEntityChange
    form_class = VATEntityChangeForm
    template_name = 'vat_entity_change/form.html'
    success_url = reverse_lazy('registration:vat_entity_change_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯營業人變更登記'
        return context

class VATEntityChangeDeleteView(LoginRequiredMixin, DeleteView):
    model = VATEntityChange
    template_name = 'vat_entity_change/confirm_delete.html'
    success_url = reverse_lazy('registration:vat_entity_change_list')
