from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from modules.basic_data.models import Customer
from core.mixins import ListActionMixin

class CustomerListView(ListActionMixin, ListView):
    model = Customer
    template_name = 'customer/list.html'
    context_object_name = 'customers'
    create_button_label = '新增客戶'  # Customize create button label

from django.db import transaction
from ..forms import ContactInlineFormSet
from core.mixins import CopyMixin

class CustomerCreateView(CopyMixin, CreateView):
    model = Customer
    template_name = 'customer/form.html'
    fields = [
        'tax_id', 'name', 'email', 'phone', 'mobile', 'source', 'line_id', 'room_id',
        'registered_zip', 'registered_address', 'correspondence_zip', 'correspondence_address',
        'bank_account_last5', 'labor_ins_code', 'health_ins_code', 'contact_person'
    ]
    success_url = reverse_lazy('customer_list')
    
    def get_copy_exclude_fields(self):
        """Exclude unique fields from being copied"""
        base_excluded = super().get_copy_exclude_fields()
        # Add tax_id to excluded fields because it's unique
        return base_excluded + ['tax_id']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pre-calculate Source Options to avoid template syntax errors
        form = context['form']
        source_field = form['source']
        current_value = source_field.value()
        
        # Handle initial value for CreateView if not bound
        if current_value is None and 'initial' in kwargs:
             current_value = kwargs['initial'].get('source')

        options = []
        for value, label in source_field.field.choices:
            # Ensure value comparison is robust (string vs int)
            is_selected = str(value) == str(current_value) if current_value is not None else False
            options.append({
                'value': value,
                'label': label,
                'selected': is_selected
            })
        context['source_options'] = options

        if self.request.POST:
            context['contact_formset'] = ContactInlineFormSet(self.request.POST)
        else:
            context['contact_formset'] = ContactInlineFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        contact_formset = context['contact_formset']
        with transaction.atomic():
            self.object = form.save()
            if contact_formset.is_valid():
                contact_formset.instance = self.object
                contact_formset.save()
            else:
                messages.error(self.request, f"聯絡人資料有誤: {contact_formset.errors}")
                return self.form_invalid(form)
        return super().form_valid(form)

from core.mixins import PrevNextMixin

class CustomerUpdateView(PrevNextMixin, UpdateView):
    model = Customer
    template_name = 'customer/form.html'
    fields = [
        'tax_id', 'name', 'email', 'phone', 'mobile', 'source', 'line_id', 'room_id',
        'registered_zip', 'registered_address', 'correspondence_zip', 'correspondence_address',
        'bank_account_last5', 'labor_ins_code', 'health_ins_code', 'contact_person'
    ]
    success_url = reverse_lazy('customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pre-calculate Source Options
        form = context['form']
        source_field = form['source']
        current_value = source_field.value()
        options = []
        for value, label in source_field.field.choices:
            is_selected = str(value) == str(current_value) if current_value is not None else False
            options.append({
                'value': value,
                'label': label,
                'selected': is_selected
            })
        context['source_options'] = options

        if self.request.POST:
            context['contact_formset'] = ContactInlineFormSet(self.request.POST, instance=self.object)
        else:
            context['contact_formset'] = ContactInlineFormSet(instance=self.object)

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
        context = self.get_context_data()
        contact_formset = context['contact_formset']
        with transaction.atomic():
            self.object = form.save()
            if contact_formset.is_valid():
                contact_formset.save()
            else:
                messages.error(self.request, f"聯絡人資料有誤: {contact_formset.errors}")
                return self.form_invalid(form)
        return super().form_valid(form)


class CustomerDeleteView(DeleteView):
    model = Customer
    template_name = 'customer/confirm_delete.html'
    success_url = reverse_lazy('customer_list')
