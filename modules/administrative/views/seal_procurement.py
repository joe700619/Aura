from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.db import transaction
from django.contrib import messages
from core.mixins import CopyMixin, PrevNextMixin
from ..models import SealProcurement
from ..forms import SealProcurementForm, SealProcurementItemFormSet


class SealProcurementListView(LoginRequiredMixin, ListView):
    model = SealProcurement
    template_name = 'administrative/seal_procurement/list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '印章採購管理'
        return context


class SealProcurementCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = SealProcurement
    form_class = SealProcurementForm
    template_name = 'administrative/seal_procurement/form.html'

    def get_success_url(self):
        return reverse_lazy('administrative:seal_procurement_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增印章採購單'
        if self.request.POST:
            context['formset'] = SealProcurementItemFormSet(self.request.POST)
        else:
            context['formset'] = SealProcurementItemFormSet()
        return context

    def form_valid(self, form):
        formset = SealProcurementItemFormSet(self.request.POST)
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            self.object.recalculate_subtotal()
            messages.success(self.request, '印章採購單已建立。')
        return redirect(self.get_success_url())


class SealProcurementUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = SealProcurement
    form_class = SealProcurementForm
    template_name = 'administrative/seal_procurement/form.html'
    success_url = reverse_lazy('administrative:seal_procurement_list')
    prev_next_order_field = '-created_at'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯印章採購單 - {self.object.company_name}'
        if self.request.POST:
            context['formset'] = SealProcurementItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = SealProcurementItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        formset = SealProcurementItemFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            formset.save()
            self.object.recalculate_subtotal()
            messages.success(self.request, '印章採購單已更新。')
        return redirect('administrative:seal_procurement_update', pk=self.object.pk)


class SealProcurementDeleteView(LoginRequiredMixin, DeleteView):
    model = SealProcurement
    success_url = reverse_lazy('administrative:seal_procurement_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
