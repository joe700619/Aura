from django.views.generic import ListView, View
from django.http import JsonResponse
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

class CustomerInfoApiView(View):
    def get(self, request, *args, **kwargs):
        customer_id = request.GET.get('id')
        if not customer_id:
            return JsonResponse({'error': 'Missing id'}, status=400)
            
        try:
            customer = Customer.objects.prefetch_related('contacts').get(pk=customer_id)
            # Find a primary or first contact
            contact = customer.contacts.first()
            contact_name = contact.name if contact else ''
            
            return JsonResponse({
                'id': customer.id,
                'name': customer.name,
                'tax_id': customer.tax_id or '',
                'address': customer.contact_address or customer.registered_address or '',
                'contact_person': contact_name
            })
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

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
