from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView
from core.mixins import BusinessRequiredMixin, FilterMixin, ListActionMixin, PrevNextMixin, EmployeeDataIsolationMixin, SearchMixin
from ..models import BookkeepingClient, ConvenienceBagLog, AccountingBookLog
from django.forms import inlineformset_factory
from django import forms


class ConvenienceBagForm(forms.ModelForm):
    class Meta:
        model = BookkeepingClient
        fields = ['last_convenience_bag_date', 'last_convenience_bag_qty', 'notes']
        widgets = {
            'last_convenience_bag_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            'last_convenience_bag_qty': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': '3'
            }),
        }


class ConvenienceBagListView(FilterMixin, EmployeeDataIsolationMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = BookkeepingClient
    template_name = 'bookkeeping/convenience_bag/list.html'
    context_object_name = 'clients'
    employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']
    search_fields = ['name', 'tax_id']
    paginate_by = 25
    default_filter = 'active'
    filter_choices = {
        'active':      {'acceptance_status': 'active'},
        'suspended':   {'acceptance_status': 'suspended'},
        'transferred': {'acceptance_status': 'transferred'},
    }

    # We do NOT allow creating a new client from here, this is just for updating bag info.
    create_button_label = None

    def get_base_queryset(self):
        return super().get_base_queryset().select_related(
            'group_assistant', 'bookkeeping_assistant'
        )

    def _base_qs_for_counts(self):
        return self.get_base_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fc = context['filter_counts']
        context['count_active']      = fc['active']
        context['count_suspended']   = fc['suspended']
        context['count_transferred'] = fc['transferred']
        return context

# ── Inline Formsets ──
ConvenienceBagLogFormSet = inlineformset_factory(
    BookkeepingClient,
    ConvenienceBagLog,
    fields=['date', 'quantity'],
    extra=0,
    can_delete=True,
)

AccountingBookLogFormSet = inlineformset_factory(
    BookkeepingClient,
    AccountingBookLog,
    fields=['date', 'year', 'cd_rom', 'sales_invoice_qty', 'receipt_form'],
    extra=0,
    can_delete=True,
)


class ConvenienceBagUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = BookkeepingClient
    form_class = ConvenienceBagForm
    template_name = 'bookkeeping/convenience_bag/form.html'
    success_url = reverse_lazy('bookkeeping:convenience_bag_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            context['convenience_bag_formset'] = ConvenienceBagLogFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['accounting_book_formset'] = AccountingBookLogFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['convenience_bag_formset'] = ConvenienceBagLogFormSet(instance=self.object)
            context['accounting_book_formset'] = AccountingBookLogFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        convenience_bag_formset = context['convenience_bag_formset']
        accounting_book_formset = context['accounting_book_formset']
        
        from django.db import transaction
        with transaction.atomic():
            self.object = form.save()
            for formset in [convenience_bag_formset, accounting_book_formset]:
                if formset.is_valid():
                    formset.instance = self.object
                    formset.save()
        return super().form_valid(form)
