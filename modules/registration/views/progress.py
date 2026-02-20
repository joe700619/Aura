from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models.progress import Progress
from ..forms import ProgressForm
from django.db.models import Q

class ProgressListView(LoginRequiredMixin, ListView):
    model = Progress
    template_name = 'progress/list.html'
    context_object_name = 'progress_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        search_query = self.request.GET.get('q')

        if status_filter:
            queryset = queryset.filter(progress_status=status_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(registration_no__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(main_contact__icontains=search_query) |
                Q(unified_business_no__icontains=search_query)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_status = self.request.GET.get('status', '')
        
        # Prepare status choices with selection state
        status_options = []
        for value, label in Progress.ProgressStatus.choices:
            status_options.append({
                'value': value,
                'label': label,
                'selected': str(value) == current_status
            })
            
        context['status_options'] = status_options
        
        # Context for list_view.html component
        context['model_name'] = 'registration:progress'
        context['model_app_label'] = 'registration'
        context['create_button_label'] = '新增案件'
        return context

class ProgressCreateView(LoginRequiredMixin, CreateView):
    model = Progress
    form_class = ProgressForm
    template_name = 'progress/form.html'
    success_url = reverse_lazy('registration:progress_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增登記進度'
        return context

class ProgressUpdateView(LoginRequiredMixin, UpdateView):
    model = Progress
    form_class = ProgressForm
    template_name = 'progress/form.html'
    success_url = reverse_lazy('registration:progress_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯登記進度'
        return context

class ProgressDeleteView(LoginRequiredMixin, DeleteView):
    model = Progress
    success_url = reverse_lazy('registration:progress_list')
    template_name = 'progress/confirm_delete.html' 

from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

class PaymentLinkGenerateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        progress = get_object_or_404(Progress, pk=pk)
        
        # Try to save the form data first
        form = ProgressForm(request.POST, instance=progress)
        if form.is_valid():
            form.save()
            messages.success(request, '資料已儲存並生成支付連結')
        else:
            messages.warning(request, '資料驗證失敗，僅生成支付連結 (使用現有資料)')
            # You might want to log form.errors here for debugging
            
        progress.generate_payment_token()
        return redirect('registration:progress_edit', pk=pk)
