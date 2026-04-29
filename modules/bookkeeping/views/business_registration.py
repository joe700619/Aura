from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView, UpdateView
from django.forms import inlineformset_factory

from core.mixins import (
    BusinessRequiredMixin, FilterMixin, ListActionMixin,
    SearchMixin, SortMixin, EmployeeDataIsolationMixin, PrevNextMixin,
)
from ..models import BookkeepingClient, BusinessRegistration, BusinessRegistrationDocument


BusinessRegistrationDocumentFormSet = inlineformset_factory(
    BusinessRegistration,
    BusinessRegistrationDocument,
    fields=['document_date', 'name', 'file'],
    extra=0,
    can_delete=True,
)


class BusinessRegistrationListView(
    FilterMixin, EmployeeDataIsolationMixin, ListActionMixin, SearchMixin,
    SortMixin, BusinessRequiredMixin, ListView,
):
    """商工登記列表 — 顯示所有有商工登記的記帳客戶"""
    model = BookkeepingClient
    template_name = 'bookkeeping/business_registration/list.html'
    context_object_name = 'clients'
    employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']
    search_fields = ['name', 'tax_id']
    allowed_sort_fields = [
        'name', 'tax_id', 'bookkeeping_assistant__name', 'group_assistant__name',
    ]
    paginate_by = 25
    default_filter = 'active'
    filter_choices = {
        'active':      {'acceptance_status': 'active'},
        'suspended':   {'acceptance_status': 'suspended'},
        'transferred': {'acceptance_status': 'transferred'},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().filter(
            business_registration__isnull=False,
        ).select_related(
            'business_registration', 'group_assistant', 'bookkeeping_assistant',
        )

    def _base_qs_for_counts(self):
        return self.get_base_queryset()

    def get_ordering(self):
        return ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        sort = self.request.GET.get('sort', '').strip()
        field_to_check = sort.lstrip('-')
        if sort and field_to_check in self.allowed_sort_fields:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fc = context['filter_counts']
        context['count_active']      = fc['active']
        context['count_suspended']   = fc['suspended']
        context['count_transferred'] = fc['transferred']
        return context


class BusinessRegistrationUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    """商工登記編輯 — 透過 BookkeepingClient pk 載入對應的 BusinessRegistration。"""
    model = BusinessRegistration
    template_name = 'bookkeeping/business_registration/form.html'
    fields = []  # 沒有主表單欄位，只有 inline formset

    def get_object(self, queryset=None):
        client_pk = self.kwargs['pk']
        client = BookkeepingClient.objects.get(pk=client_pk, is_deleted=False)
        obj, _ = BusinessRegistration.objects.get_or_create(client=client)
        return obj

    def get_success_url(self):
        return reverse('bookkeeping:business_registration_update', kwargs={'pk': self.object.client.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.object.client
        if self.request.method == 'POST':
            context['document_formset'] = BusinessRegistrationDocumentFormSet(
                self.request.POST, self.request.FILES,
                instance=self.object, prefix='documents',
            )
        else:
            context['document_formset'] = BusinessRegistrationDocumentFormSet(
                instance=self.object, prefix='documents',
            )

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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        formset = BusinessRegistrationDocumentFormSet(
            request.POST, request.FILES, instance=self.object, prefix='documents',
        )
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
            messages.success(request, '商工登記儲存成功！')
            return redirect(self.get_success_url())
        messages.error(request, '表單內容有誤，請檢查後再試。')
        context = self.get_context_data()
        context['document_formset'] = formset
        return self.render_to_response(context)
