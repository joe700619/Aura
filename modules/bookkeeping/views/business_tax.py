from django.views.generic import ListView
from core.mixins import BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin
from ..models import BookkeepingClient

class BusinessTaxListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    """
    營業稅申報列表視圖
    顯示服務型態屬於營業人類（VAT_SERVICE_TYPES）的客戶，方便快速進入各期申報維護。
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/business_tax/list.html'
    context_object_name = 'clients'
    search_fields = ['name', 'tax_id']
    paginate_by = 25
    filter_choices = {
        'monthly':   {'tax_setting__filing_frequency': 'monthly'},
        'bimonthly': {'tax_setting__filing_frequency': 'bimonthly'},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().filter(
            service_type__in=BookkeepingClient.VAT_SERVICE_TYPES,
            acceptance_status='active',
        ).select_related('tax_setting', 'bookkeeping_assistant').order_by('name')

    def _base_qs_for_counts(self):
        return BookkeepingClient.objects.filter(
            is_deleted=False,
            service_type__in=BookkeepingClient.VAT_SERVICE_TYPES,
            acceptance_status='active',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_monthly']   = context['filter_counts']['monthly']
        context['count_bimonthly'] = context['filter_counts']['bimonthly']
        return context
