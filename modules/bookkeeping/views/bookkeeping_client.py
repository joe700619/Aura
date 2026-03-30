from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from core.mixins import ListActionMixin, CopyMixin, PrevNextMixin, EmployeeDataIsolationMixin
from ..models import BookkeepingClient, GroupInvoice
from ..models.billing import ServiceFee
from ..forms import BookkeepingClientForm
from modules.hr.models import Employee


# ── Inline Formsets ──
GroupInvoiceFormSet = inlineformset_factory(
    BookkeepingClient,
    GroupInvoice,
    fields=['invoice_type', 'quantity'],
    extra=0,
    can_delete=True,
)

ServiceFeeFormSet = inlineformset_factory(
    BookkeepingClient,
    ServiceFee,
    fields=['service_fee', 'ledger_fee', 'billing_months', 'billing_cycle',
            'effective_date', 'end_date', 'notes'],
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
    context['billing_cycle_choices'] = ServiceFee.BillingCycle.choices

    # Invoice formset
    if request and request.method == 'POST':
        context['invoice_formset'] = GroupInvoiceFormSet(request.POST, instance=obj, prefix='group_invoices')
    elif obj:
        context['invoice_formset'] = GroupInvoiceFormSet(instance=obj, prefix='group_invoices')
    else:
        context['invoice_formset'] = GroupInvoiceFormSet(prefix='group_invoices')

    # Service Fee formset
    if request and request.method == 'POST':
        context['service_fee_formset'] = ServiceFeeFormSet(request.POST, instance=obj, prefix='service_fees')
    elif obj:
        context['service_fee_formset'] = ServiceFeeFormSet(instance=obj, prefix='service_fees')
    else:
        context['service_fee_formset'] = ServiceFeeFormSet(prefix='service_fees')

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
    'customer', 'tax_id', 'tax_registration_no', 'name', 'line_id', 'room_id',
    'contact_person', 'phone', 'mobile', 'email',
    'correspondence_address', 'registered_address',
    'acceptance_status', 'billing_status', 'service_type',
    'group_assistant', 'bookkeeping_assistant',
    'has_group_invoice',
    'send_invoice_method', 'send_merged_client_name',
    'receive_invoice_method', 'receive_merged_client_name',
    'last_convenience_bag_date', 'last_convenience_bag_qty',
    'notes', 'cost_sharing_data', 'client_source', 'contact_date', 'transfer_checklist',
    'business_password', 'national_tax_password', 'e_invoice_account', 'e_invoice_password',
]


class BookkeepingClientCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = BookkeepingClient
    template_name = 'bookkeeping/bookkeeping_client/form.html'
    form_class = BookkeepingClientForm
    success_url = reverse_lazy('bookkeeping:client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return _get_common_context(context, context['form'], request=self.request)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('bookkeeping:client_update', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        invoice_formset = context['invoice_formset']
        service_fee_formset = context['service_fee_formset']
        
        if invoice_formset.is_valid() and service_fee_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                invoice_formset.instance = self.object
                invoice_formset.save()
                service_fee_formset.instance = self.object
                service_fee_formset.save()
            from django.contrib import messages
            messages.success(self.request, '記帳客戶建立成功！')
            return redirect(self.get_success_url())
        else:
            with open('C:/Users/joe70/PythonProject/Aura/debug_form_errors.txt', 'w', encoding='utf-8') as f:
                f.write(f"CREATE VIEW ERRORS:\n")
                f.write(f"Main Form: {form.errors}\n")
                f.write(f"Invoice Formset: {invoice_formset.errors}\n")
                f.write(f"Service Fee Formset: {service_fee_formset.errors}\n")
                f.write(f"SF Non-form: {service_fee_formset.non_form_errors()}\n")
            from django.contrib import messages
            messages.error(self.request, '表單內容有誤，請檢查後再試。')
            return self.render_to_response(self.get_context_data(form=form))


class BookkeepingClientUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = BookkeepingClient
    template_name = 'bookkeeping/bookkeeping_client/form.html'
    form_class = BookkeepingClientForm
    success_url = reverse_lazy('bookkeeping:client_list')

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return _get_common_context(context, context['form'], self.object, self.request)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('bookkeeping:client_update', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        invoice_formset = context['invoice_formset']
        service_fee_formset = context['service_fee_formset']
        
        if invoice_formset.is_valid() and service_fee_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                invoice_formset.save()
                service_fee_formset.save()
            from django.contrib import messages
            messages.success(self.request, '記帳客戶更新成功！')
            return redirect(self.get_success_url())
        else:
            with open('C:/Users/joe70/PythonProject/Aura/debug_form_errors.txt', 'w', encoding='utf-8') as f:
                f.write(f"UPDATE VIEW ERRORS:\n")
                f.write(f"Main Form: {form.errors}\n")
                f.write(f"Invoice Formset: {invoice_formset.errors}\n")
                f.write(f"Service Fee Formset: {service_fee_formset.errors}\n")
                f.write(f"SF Non-form: {service_fee_formset.non_form_errors()}\n")
            from django.contrib import messages
            messages.error(self.request, '表單內容有誤，請檢查後再試。')
            return self.render_to_response(self.get_context_data(form=form))


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
