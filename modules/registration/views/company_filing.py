from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import CompanyFiling
from ..forms import CompanyFilingForm, FilingHistoryFormSet
from django.db.models import Q
from django.db import transaction

class CompanyFilingListView(LoginRequiredMixin, ListView):
    model = CompanyFiling
    template_name = 'company_filing/list.html'
    context_object_name = 'company_filing_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q')

        if search_query:
            queryset = queryset.filter(
                Q(filing_no__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(main_contact__icontains=search_query) |
                Q(unified_business_no__icontains=search_query) |
                Q(address__icontains=search_query)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '公司法22-1申報列表'
        context['model_name'] = 'registration:company_filing'
        context['model_app_label'] = 'registration'
        context['create_button_label'] = '新增申報'
        return context

class CompanyFilingCreateView(LoginRequiredMixin, CreateView):
    model = CompanyFiling
    form_class = CompanyFilingForm
    template_name = 'company_filing/form.html'
    success_url = reverse_lazy('registration:company_filing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增公司法22-1申報'
        context['action'] = 'create'
        if self.request.POST:
            context['history_formset'] = FilingHistoryFormSet(self.request.POST)
        else:
            context['history_formset'] = FilingHistoryFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        history_formset = context['history_formset']
        with transaction.atomic():
            self.object = form.save()
            if history_formset.is_valid():
                history_formset.instance = self.object
                history_formset.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)

class CompanyFilingUpdateView(LoginRequiredMixin, UpdateView):
    model = CompanyFiling
    form_class = CompanyFilingForm
    template_name = 'company_filing/form.html'
    success_url = reverse_lazy('registration:company_filing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯公司法22-1申報'
        context['action'] = 'update'
        if self.request.POST:
            context['history_formset'] = FilingHistoryFormSet(self.request.POST, instance=self.object)
        else:
            context['history_formset'] = FilingHistoryFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        history_formset = context['history_formset']
        with transaction.atomic():
            self.object = form.save()
            if history_formset.is_valid():
                history_formset.instance = self.object
                history_formset.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)

class CompanyFilingDeleteView(LoginRequiredMixin, DeleteView):
    model = CompanyFiling
    success_url = reverse_lazy('registration:company_filing_list')
    template_name = 'company_filing/confirm_delete.html'
