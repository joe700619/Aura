from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect

from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin
from ..models import ServiceRemunerationTaxRate, NHIConfig
from modules.client_portal.forms_remuneration import TaxRateForm


class ServiceRemunerationTaxRateListView(ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = ServiceRemunerationTaxRate
    template_name = 'bookkeeping/service_remuneration_tax_rate/list.html'
    context_object_name = 'rates'
    paginate_by = 50
    search_fields = ['code', 'label']
    create_button_label = '新增稅率'

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False).order_by('sort_order', 'code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nhi_config'] = NHIConfig.get_solo()
        return context


class ServiceRemunerationTaxRateCreateView(BusinessRequiredMixin, CreateView):
    model = ServiceRemunerationTaxRate
    form_class = TaxRateForm
    template_name = 'bookkeeping/service_remuneration_tax_rate/form.html'
    success_url = reverse_lazy('bookkeeping:service_remuneration_tax_rate_list')


class ServiceRemunerationTaxRateUpdateView(BusinessRequiredMixin, UpdateView):
    model = ServiceRemunerationTaxRate
    form_class = TaxRateForm
    template_name = 'bookkeeping/service_remuneration_tax_rate/form.html'
    success_url = reverse_lazy('bookkeeping:service_remuneration_tax_rate_list')


class ServiceRemunerationTaxRateDeleteView(BusinessRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        obj = get_object_or_404(ServiceRemunerationTaxRate, pk=pk)
        obj.is_deleted = True
        obj.save(update_fields=['is_deleted'])
        return redirect('bookkeeping:service_remuneration_tax_rate_list')


class NHIConfigUpdateView(BusinessRequiredMixin, View):
    """更新 NHI 設定（singleton — 只取/編第一筆）。"""

    def post(self, request, *args, **kwargs):
        from decimal import Decimal
        obj = NHIConfig.get_solo()
        try:
            obj.threshold = Decimal(request.POST.get('threshold') or '0')
            obj.rate = Decimal(request.POST.get('rate') or '0')
            obj.save()
        except Exception:
            pass
        return redirect('bookkeeping:service_remuneration_tax_rate_list')
