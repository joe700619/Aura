from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from core.mixins import ListActionMixin, CopyMixin, PrevNextMixin
from ..models import ServiceItem
from ..forms import ServiceItemForm

class ServiceItemListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = ServiceItem
    template_name = 'service_items/list.html'
    context_object_name = 'service_items'
    paginate_by = 20
    create_button_label = '新增服務項目'

class ServiceItemCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = 'service_items/form.html'
    success_url = reverse_lazy('service_item_list')

class ServiceItemUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = 'service_items/form.html'
    success_url = reverse_lazy('service_item_list')
    prev_next_order_field = 'service_id'

class ServiceItemDeleteView(LoginRequiredMixin, DeleteView):
    model = ServiceItem
    success_url = reverse_lazy('service_item_list')
    template_name = 'service_items/confirm_delete.html'
