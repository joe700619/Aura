from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.contrib import messages
from core.mixins import CopyMixin, PrevNextMixin, ListActionMixin, SoftDeleteMixin
from ..models import Contact
from ..forms import ContactForm

class ContactListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = Contact
    template_name = 'contact/list.html'
    context_object_name = 'contacts'
    paginate_by = 20
    create_button_label = '新增聯絡人'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['custom_create_url'] = reverse_lazy('basic_data:contact_create')
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q) | queryset.filter(phone__icontains=q) | queryset.filter(mobile__icontains=q)
        return queryset

class ContactCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'contact/form.html'
    copy_exclude_fields = []  # Copy all fields by default

    def get_success_url(self):
        messages.success(self.request, "聯絡人已成功建立！")
        return reverse_lazy('basic_data:contact_update', kwargs={'pk': self.object.pk})

class ContactUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = 'contact/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, "聯絡人已成功更新！")
        return reverse_lazy('basic_data:contact_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # History for sidebar - Process in view to avoid template filter issues
        history_list = []
        for record in self.object.history.all()[:10]:
            history_list.append({
                'history_user': record.history_user,
                'history_date': record.history_date,
                'history_type': record.history_type,
                'history_change_reason': record.history_change_reason or "資料變更",
            })
        context['history'] = history_list
        return context

class ContactDeleteView(SoftDeleteMixin, LoginRequiredMixin, DeleteView):
    model = Contact
    success_url = reverse_lazy('basic_data:contact_list')
    template_name = 'contact/confirm_delete.html'

class ContactHistoryView(LoginRequiredMixin, ListView):
    template_name = "contact/history.html"
    context_object_name = "history"
    paginate_by = 20

    def get_queryset(self):
        contact = get_object_or_404(Contact, pk=self.kwargs['pk'])
        return contact.history.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact'] = get_object_or_404(Contact, pk=self.kwargs['pk'])
        return context
