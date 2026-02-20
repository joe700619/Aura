from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from core.mixins import ListActionMixin, PrevNextMixin
from ..models import Shareholder
from ..forms import ShareholderForm

class ShareholderListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = Shareholder
    template_name = 'shareholder/list.html'
    context_object_name = 'shareholders'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Status Filter
        status = self.request.GET.get('status', 'ACTIVE')
        if status == 'ACTIVE':
            queryset = queryset.filter(is_active=True)
        elif status == 'INACTIVE':
            queryset = queryset.filter(is_active=False)
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(id_number__icontains=q)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', 'ACTIVE')
        return context

class ShareholderCreateView(LoginRequiredMixin, CreateView):
    model = Shareholder
    form_class = ShareholderForm
    template_name = 'shareholder/form.html'
    success_url = reverse_lazy('registration:shareholder_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        return context

class ShareholderUpdateView(LoginRequiredMixin, PrevNextMixin, UpdateView):
    model = Shareholder
    form_class = ShareholderForm
    template_name = 'shareholder/form.html'
    success_url = reverse_lazy('registration:shareholder_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'update'
        return context

class ShareholderDeleteView(LoginRequiredMixin, DeleteView):
    model = Shareholder
    template_name = 'shareholder/confirm_delete.html'
    success_url = reverse_lazy('registration:shareholder_list')
