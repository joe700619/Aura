from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from core.mixins import ListActionMixin
from ..models import IndustryTaxRate

class IndustryTaxRateListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = IndustryTaxRate
    template_name = 'bookkeeping/industry_tax_rate_list.html'
    context_object_name = 'rates'
    paginate_by = 50
    # No create button for this read-only view
