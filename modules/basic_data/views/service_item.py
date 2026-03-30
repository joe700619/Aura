from django.contrib import messages
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

    def get_success_url(self):
        messages.success(self.request, f"服務項目「{self.object.name}」已新增成功！")
        return reverse_lazy('basic_data:service_item_update', kwargs={'pk': self.object.pk})

class ServiceItemUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = 'service_items/form.html'
    prev_next_order_field = 'service_id'

    def get_success_url(self):
        messages.success(self.request, f"服務項目「{self.object.name}」已更新成功！")
        return reverse_lazy('basic_data:service_item_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object and hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or "資料變更",
                })
            context['history'] = history_list
        return context

class ServiceItemDeleteView(LoginRequiredMixin, DeleteView):
    model = ServiceItem
    success_url = reverse_lazy('basic_data:service_item_list')
    template_name = 'service_items/confirm_delete.html'
