from django.views.generic import ListView
from modules.bookkeeping.models.vat import VAT

class VATListView(ListView):
    model = VAT
    template_name = 'vat/list.html'
    context_object_name = 'vat_records'
