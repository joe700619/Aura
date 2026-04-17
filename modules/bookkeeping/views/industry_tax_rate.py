from django.views.generic import ListView
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin
from ..models import IndustryTaxRate

class IndustryTaxRateListView(ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = IndustryTaxRate
    template_name = 'bookkeeping/industry_tax_rate_list.html'
    context_object_name = 'rates'
    paginate_by = 50
    search_fields = ['industry_code', 'industry_name']
    # No create button for this read-only view
