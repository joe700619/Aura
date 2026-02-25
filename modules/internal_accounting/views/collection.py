from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from ..models import Collection, Receivable
from ..forms import CollectionForm

class CollectionListView(LoginRequiredMixin, ListView):
    model = Collection
    template_name = 'collection/list.html'
    context_object_name = 'collections'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '收款管理'
        context['model_name'] = 'internal_accounting:collection'
        context['model_app_label'] = 'internal_accounting'
        context['create_button_label'] = '新增收款紀錄'
        return context

class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = 'collection/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:collection_edit', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        receivable_id = self.request.GET.get('receivable_id')
        if receivable_id:
            receivable = get_object_or_404(Receivable, pk=receivable_id)
            initial['receivable'] = receivable
            
            # Additional pre-fill fields
            for field in ['amount', 'tax', 'fee', 'allowance']:
                val = self.request.GET.get(field)
                if val:
                    try:
                        initial[field] = float(val)
                    except (ValueError, TypeError):
                        pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增收款紀錄'
        context['action'] = 'create'
        receivable_id = self.request.GET.get('receivable_id')
        if receivable_id:
            context['prefilled_receivable'] = get_object_or_404(Receivable, pk=receivable_id)
        return context

    def form_valid(self, form):
        messages.success(self.request, "收款紀錄已建立")
        return super().form_valid(form)

class CollectionUpdateView(LoginRequiredMixin, UpdateView):
    model = Collection
    form_class = CollectionForm
    template_name = 'collection/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:collection_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯收款紀錄: {self.object.collection_no}'
        context['action'] = 'update'

        # History Logic for Sidebar
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

    def form_valid(self, form):
        messages.success(self.request, "收款紀錄已更新")
        return super().form_valid(form)

class CollectionDeleteView(LoginRequiredMixin, DeleteView):
    model = Collection
    template_name = 'collection/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:collection_list')

def search_receivables(request):
    query = request.GET.get('q', '')
    receivables = Receivable.objects.filter(
        Q(company_name__icontains=query) |
        Q(unified_business_no__icontains=query) |
        Q(receivable_no__icontains=query)
    ).order_by('company_name')[:20]
    
    return render(request, 'internal_accounting/partials/receivable_search_results.html', {
        'receivables': receivables
    })
