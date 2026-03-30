from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from core.mixins import ListActionMixin
from ..models import SystemBulletin
from ..forms import SystemBulletinCRUDForm

class SystemBulletinListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = SystemBulletin
    template_name = 'administrative/bulletin/list.html'
    context_object_name = 'object_list'
    create_button_label = _('新增公佈欄')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('系統公佈欄')
        context['custom_create_url'] = reverse_lazy('administrative:system_bulletin_create')
        return context

class SystemBulletinCreateView(LoginRequiredMixin, CreateView):
    model = SystemBulletin
    form_class = SystemBulletinCRUDForm
    template_name = 'administrative/bulletin/form.html'
    success_url = reverse_lazy('administrative:system_bulletin_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('新增公佈欄')
        return context

class SystemBulletinUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = SystemBulletin
    form_class = SystemBulletinCRUDForm
    template_name = 'administrative/bulletin/form.html'
    success_url = reverse_lazy('administrative:system_bulletin_list')
    success_message = _("公佈欄已成功更新")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('編輯公佈欄')
        return context

class SystemBulletinDeleteView(LoginRequiredMixin, DeleteView):
    model = SystemBulletin
    success_url = reverse_lazy('administrative:system_bulletin_list')
    
    def form_valid(self, form):
        from django.contrib import messages
        messages.success(self.request, _('公佈欄已成功刪除。'))
        return super().form_valid(form)
