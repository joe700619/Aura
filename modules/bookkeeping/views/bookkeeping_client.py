from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.views import View
from django.db import models, transaction
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from core.mixins import BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin, CopyMixin, PrevNextMixin, EmployeeDataIsolationMixin, SortMixin
from ..models import BookkeepingClient, GroupInvoice
from ..models.tax_unit import TaxUnit
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


class BookkeepingClientListView(FilterMixin, EmployeeDataIsolationMixin, ListActionMixin, SearchMixin, SortMixin, BusinessRequiredMixin, ListView):
    model = BookkeepingClient
    template_name = 'bookkeeping/bookkeeping_client/list.html'
    context_object_name = 'clients'
    create_button_label = '新增記帳客戶'
    employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']
    search_fields = ['name', 'tax_id']
    allowed_sort_fields = [
        'name', 'tax_id', 'acceptance_status', 'billing_status',
        'service_type', 'group_assistant__name', 'bookkeeping_assistant__name',
        'annotated_billing_cycle'
    ]
    paginate_by = 25
    default_filter = 'active'
    filter_choices = {
        'active':      {'acceptance_status': 'active'},
        'suspended':   {'acceptance_status': 'suspended'},
        'transferred': {'acceptance_status': 'transferred'},
    }

    def get_base_queryset(self):
        from django.db.models import OuterRef, Subquery
        from django.utils import timezone
        
        today = timezone.now().date()
        active_sf_cycle = ServiceFee.objects.filter(
            client=OuterRef('pk'),
            effective_date__lte=today,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).order_by('-effective_date').values('billing_cycle')[:1]
        
        return super().get_base_queryset().select_related(
            'group_assistant', 'bookkeeping_assistant'
        ).prefetch_related('service_fees').annotate(
            annotated_billing_cycle=Subquery(active_sf_cycle)
        )

    def _base_qs_for_counts(self):
        # Use get_base_queryset so counts respect employee isolation
        return self.get_base_queryset()

    def get_ordering(self):
        # 避免 ListView 預設去對尚未產生的 annotated_billing_cycle 做排序導致報錯
        return ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        sort = self.request.GET.get('sort', '').strip()
        field_to_check = sort.lstrip('-')
        if sort and field_to_check in self.allowed_sort_fields:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_active']      = context['filter_counts']['active']
        context['count_suspended']   = context['filter_counts']['suspended']
        context['count_transferred'] = context['filter_counts']['transferred']
        return context


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
        form['send_invoice_method'].value(),
    )
    context['receive_invoice_method_options'] = _build_select_options(
        BookkeepingClient.ReceiveInvoiceMethod.choices,
        form['receive_invoice_method'].value(),
    )
    context['client_source_options'] = _build_select_options(
        BookkeepingClient.ClientSource.choices,
        form['client_source'].value(),
    )
    context['notification_method_options'] = _build_select_options(
        BookkeepingClient.NotificationMethod.choices,
        form['notification_method'].value(),
    )
    context['payment_method_options'] = _build_select_options(
        BookkeepingClient.PaymentMethod.choices,
        form['payment_method'].value(),
    )
    context['employees'] = Employee.objects.filter(is_active=True).order_by('name')
    context['tax_units'] = TaxUnit.objects.order_by('city_id', 'unit_code')
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

    # Active service fee (for display in Card 3)
    if obj:
        from django.utils import timezone
        today = timezone.now().date()
        active_sf = obj.service_fees.filter(
            effective_date__lte=today,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).order_by('-effective_date').first()
        context['active_service_fee'] = active_sf
    else:
        context['active_service_fee'] = None

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
    'national_tax_password', 'e_invoice_account', 'e_invoice_password',
]


class BookkeepingClientCreateView(CopyMixin, BusinessRequiredMixin, CreateView):
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
            from django.contrib import messages
            messages.error(self.request, '表單內容有誤，請檢查後再試。')
            return self.render_to_response(self.get_context_data(form=form))


class BookkeepingClientUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
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
            from django.contrib import messages
            messages.error(self.request, '表單內容有誤，請檢查後再試。')
            return self.render_to_response(self.get_context_data(form=form))


class BookkeepingClientDeleteView(BusinessRequiredMixin, View):
    """Soft-delete: GET shows confirmation, POST sets is_deleted=True."""

    def get(self, request, pk):
        obj = get_object_or_404(BookkeepingClient, pk=pk, is_deleted=False)
        return render(request, 'bookkeeping/bookkeeping_client/confirm_delete.html', {'object': obj})

    def post(self, request, pk):
        obj = get_object_or_404(BookkeepingClient, pk=pk, is_deleted=False)
        obj.is_deleted = True
        obj.save()
        return redirect(reverse_lazy('bookkeeping:client_list'))
