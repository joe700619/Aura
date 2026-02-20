from django.views.generic import ListView
from modules.bookkeeping.models.income_tax import IncomeTax

class IncomeTaxListView(ListView):
    model = IncomeTax
    template_name = 'income_tax/list.html'
    context_object_name = 'tax_records'
