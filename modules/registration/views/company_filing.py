from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.mixins import BusinessRequiredMixin, ListActionMixin, FilterMixin, SearchMixin, SortMixin, PrevNextMixin, SoftDeleteMixin
from django.contrib import messages
from ..models import CompanyFiling
from ..forms import CompanyFilingForm, FilingHistoryFormSet
from django.db import transaction

class CompanyFilingListView(SortMixin, FilterMixin, SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    model = CompanyFiling
    template_name = 'company_filing/list.html'
    context_object_name = 'company_filing_list'
    paginate_by = 25
    search_fields = ['filing_no', 'company_name', 'main_contact', 'unified_business_no', 'address']
    filter_choices = {
        'OFFICE': {'filing_method': 'OFFICE'},
        'SELF':   {'filing_method': 'SELF'},
    }
    allowed_sort_fields = ['filing_no', 'company_name', 'unified_business_no', 'main_contact', 'filing_method', 'fee']
    default_sort = ['-filing_no']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_all']    = context['filter_counts']['ALL']
        context['count_office'] = context['filter_counts']['OFFICE']
        context['count_self']   = context['filter_counts']['SELF']
        return context

class CompanyFilingCreateView(BusinessRequiredMixin, CreateView):
    model = CompanyFiling
    form_class = CompanyFilingForm
    template_name = 'company_filing/form.html'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:company_filing_edit', kwargs={'pk': self.object.pk})

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

class CompanyFilingUpdateView(BusinessRequiredMixin, PrevNextMixin, UpdateView):
    model = CompanyFiling
    form_class = CompanyFilingForm
    template_name = 'company_filing/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:company_filing_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯公司法22-1申報'
        context['action'] = 'update'
        if self.request.POST:
            context['history_formset'] = FilingHistoryFormSet(self.request.POST, instance=self.object)
        else:
            context['history_formset'] = FilingHistoryFormSet(instance=self.object)
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

class CompanyFilingDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = CompanyFiling
    success_url = reverse_lazy('registration:company_filing_list')
    template_name = 'company_filing/confirm_delete.html'
