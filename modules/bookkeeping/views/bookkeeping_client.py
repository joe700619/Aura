from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from core.mixins import ListActionMixin, CopyMixin, PrevNextMixin, EmployeeDataIsolationMixin
from ..models import BookkeepingClient, GroupInvoice
from modules.hr.models import Employee


# ── Inline Formset ──
GroupInvoiceFormSet = inlineformset_factory(
    BookkeepingClient,
    GroupInvoice,
    fields=['invoice_type', 'quantity'],
    extra=0,
    can_delete=True,
)


class BookkeepingClientListView(EmployeeDataIsolationMixin, ListActionMixin, LoginRequiredMixin, ListView):
    model = BookkeepingClient
    template_name = 'bookkeeping/bookkeeping_client/list.html'
    context_object_name = 'clients'
    create_button_label = '新增記帳客戶'
    employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']

    def get_queryset(self):
        # The mixin handles the role-based filtering and returns the filtered qs
        return super().get_queryset().filter(is_deleted=False).select_related(
            'group_assistant', 'bookkeeping_assistant'
        )


def _build_select_options(choices, current_value):
    """Helper to build option dicts for select dropdowns."""
    options = []
    for value, label in choices:
        options.append({
            'value': value,
            'label': label,
            'selected': str(value) == str(current_value) if current_value else False,
        })
    return options


def _get_common_context(context, form, obj=None, request=None):
    """Add common context for both Create and Update views."""
    context['acceptance_status_options'] = _build_select_options(
        BookkeepingClient.AcceptanceStatus.choices,
        form['acceptance_status'].value(),
    )
    context['billing_status_options'] = _build_select_options(
        BookkeepingClient.BillingStatus.choices,
        form['billing_status'].value(),
    )
    context['service_type_options'] = _build_select_options(
        BookkeepingClient.ServiceType.choices,
        form['service_type'].value(),
    )
    context['send_invoice_method_options'] = _build_select_options(
        BookkeepingClient.SendInvoiceMethod.choices,
        form['send_invoice_method'].value() if 'send_invoice_method' in form else None,
    )
    context['receive_invoice_method_options'] = _build_select_options(
        BookkeepingClient.ReceiveInvoiceMethod.choices,
        form['receive_invoice_method'].value() if 'receive_invoice_method' in form else None,
    )
    context['client_source_options'] = _build_select_options(
        BookkeepingClient.ClientSource.choices,
        form['client_source'].value() if 'client_source' in form else None,
    )
    context['employees'] = Employee.objects.filter(is_active=True).order_by('name')
    context['invoice_type_choices'] = GroupInvoice.InvoiceType.choices

    # Invoice formset
    if request and request.method == 'POST':
        context['invoice_formset'] = GroupInvoiceFormSet(request.POST, instance=obj)
    elif obj:
        context['invoice_formset'] = GroupInvoiceFormSet(instance=obj)
    else:
        context['invoice_formset'] = GroupInvoiceFormSet()

    # History (only for existing objects)
    if obj and hasattr(obj, 'history'):
        history_list = []
        for record in obj.history.all().select_related('history_user').order_by('-history_date')[:10]:
            history_list.append({
                'history_user': record.history_user,
                'history_date': record.history_date,
                'history_type': record.history_type,
                'history_change_reason': record.history_change_reason or '資料變更',
            })
        context['history'] = history_list
    return context


BOOKKEEPING_CLIENT_FIELDS = [
    'tax_id', 'tax_registration_no', 'name', 'line_id', 'room_id',
    'contact_person', 'phone', 'mobile', 'email',
    'correspondence_address', 'registered_address',
    'acceptance_status', 'billing_status', 'service_type',
    'group_assistant', 'bookkeeping_assistant',
    'has_group_invoice',
    'send_invoice_method', 'send_merged_client_name',
    'receive_invoice_method', 'receive_merged_client_name',
    'last_convenience_bag_date', 'last_convenience_bag_qty',
    'notes', 'cost_sharing_data', 'client_source', 'contact_date', 'transfer_checklist',
    'business_password', 'e_invoice_account', 'e_invoice_password',
]


class BookkeepingClientCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = BookkeepingClient
    template_name = 'bookkeeping/bookkeeping_client/form.html'
    fields = BOOKKEEPING_CLIENT_FIELDS
    success_url = reverse_lazy('bookkeeping:client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return _get_common_context(context, context['form'], request=self.request)

    def form_valid(self, form):
        context = self.get_context_data()
        invoice_formset = context['invoice_formset']
        with transaction.atomic():
            self.object = form.save()
            if invoice_formset.is_valid():
                invoice_formset.instance = self.object
                invoice_formset.save()
        return redirect(self.success_url)


class BookkeepingClientUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = BookkeepingClient
    template_name = 'bookkeeping/bookkeeping_client/form.html'
    fields = BOOKKEEPING_CLIENT_FIELDS
    success_url = reverse_lazy('bookkeeping:client_list')

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return _get_common_context(context, context['form'], self.object, self.request)

    def form_valid(self, form):
        context = self.get_context_data()
        invoice_formset = context['invoice_formset']
        with transaction.atomic():
            self.object = form.save()
            if invoice_formset.is_valid():
                invoice_formset.save()
        return redirect(self.success_url)


class BookkeepingClientDeleteView(LoginRequiredMixin, View):
    """Soft-delete: GET shows confirmation, POST sets is_deleted=True."""

    def get(self, request, pk):
        obj = get_object_or_404(BookkeepingClient, pk=pk, is_deleted=False)
        return render(request, 'bookkeeping/bookkeeping_client/confirm_delete.html', {'object': obj})

    def post(self, request, pk):
        obj = get_object_or_404(BookkeepingClient, pk=pk, is_deleted=False)
        obj.is_deleted = True
        obj.save()
        return redirect(reverse_lazy('bookkeeping:client_list'))
