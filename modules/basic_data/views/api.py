from django.views.generic import ListView
from modules.basic_data.models import Customer, Contact, ServiceItem

class CustomerSearchApiView(ListView):
    model = Customer
    template_name = 'basic_data/partials/customer_search_results.html'
    context_object_name = 'customers'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Customer.objects.filter(name__icontains=query) | Customer.objects.filter(tax_id__icontains=query)
        return Customer.objects.none()

class CustomerSearchForProgressApiView(CustomerSearchApiView):
    template_name = 'basic_data/partials/customer_search_results_progress.html'

class ContactSearchForProgressApiView(ListView):
    model = Contact
    template_name = 'basic_data/partials/contact_search_results_progress.html'
    context_object_name = 'contacts'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Contact.objects.filter(name__icontains=query) | \
                   Contact.objects.filter(phone__icontains=query) | \
                   Contact.objects.filter(mobile__icontains=query)
        return Contact.objects.none()

class ServiceItemSearchApiView(ListView):
    model = ServiceItem
    template_name = 'basic_data/partials/service_item_search_results.html'
    context_object_name = 'service_items'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return ServiceItem.objects.filter(name__icontains=query)
        return ServiceItem.objects.none()
