from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.mixins import CopyMixin, PrevNextMixin, ListActionMixin, SoftDeleteMixin
from ..models import Customer
from ..forms import ContactInlineFormSet, CustomerForm

class CustomerListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customer/list.html'
    context_object_name = 'customers'
    paginate_by = 10
    
    def get_queryset(self):
        # 預設不顯示已軟刪除的資料
        qs = super().get_queryset()
        if hasattr(self.model, 'is_deleted'):
            qs = qs.filter(is_deleted=False)
        return qs
    create_button_label = '新增客戶'  # Customize create button label

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['custom_create_url'] = reverse_lazy('basic_data:customer_create')
        return context


class CustomerCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/form.html'

    def get_success_url(self):
        messages.success(self.request, f"客戶「{self.object.name}」已新增成功！")
        return reverse_lazy('basic_data:customer_update', kwargs={'pk': self.object.pk})
    
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


class CustomerUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, f"客戶「{self.object.name}」已更新成功！")
        return reverse_lazy('basic_data:customer_update', kwargs={'pk': self.object.pk})

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


class CustomerDeleteView(SoftDeleteMixin, LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customer/confirm_delete.html'
    success_url = reverse_lazy('basic_data:customer_list')
