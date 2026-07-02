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
                'line_id': customer.line_id or '',
                'room_id': customer.room_id or '',
                'address': customer.correspondence_address or customer.registered_address or '',
                'contact_person': customer.contact_person or contact_name or '',
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
            qs = Contact.objects.filter(name__icontains=query) | \
                 Contact.objects.filter(phone__icontains=query) | \
                 Contact.objects.filter(mobile__icontains=query) | \
                 Contact.objects.filter(customer__name__icontains=query)
            return qs.select_related('customer')
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


import urllib.request
import urllib.parse
import json as json_lib

class GcisProxyApiView(View):
    """後端 Proxy：代理呼叫政府商工登記 API，避免前端 CORS 問題。"""

    def get(self, request, *args, **kwargs):
        tax_id = request.GET.get('tax_id', '').strip()

        if not tax_id or len(tax_id) != 8 or not tax_id.isdigit():
            return JsonResponse({'error': '請提供正確的8位統一編號'}, status=400)

        gcis_url = (
            "https://data.gcis.nat.gov.tw/od/data/api/"
            "5F64D864-61CB-4D0D-8AD9-492047CC1EA6"
            f"?$format=json&$filter=Business_Accounting_NO%20eq%20{tax_id}&$skip=0&$top=50"
        )

        try:
            req = urllib.request.Request(gcis_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json_lib.loads(resp.read().decode('utf-8'))

            if not data:
                return JsonResponse({'error': '查無此統編資料', 'type': 'not_found'})

            company = data[0]
            location = company.get('Company_Location', '').strip()
            company_name = company.get('Company_Name', '').strip()

            if not location:
                return JsonResponse({
                    'error': '非公司組織，請自行填入',
                    'type': 'no_location',
                    'company_name': company_name,
                })

            return JsonResponse({
                'success': True,
                'company_name': company_name,
                'registered_address': location,
                # 以下為營業人變更登記申請書套表所需的快照欄位（其他既有呼叫端會忽略）。
                'responsible_name': company.get('Responsible_Name', '').strip(),
                'capital_stock_amount': company.get('Capital_Stock_Amount'),
                'paid_in_capital_amount': company.get('Paid_In_Capital_Amount'),
            })

        except Exception as e:
            return JsonResponse({'error': f'查詢失敗：{str(e)}'}, status=500)


class GcisDirectorApiView(View):
    """後端 Proxy：查詢政府商工登記「公司董監事」資料（dataset 4E5F7653），
    供董監事名單 Tab 與系統資料核對一致性使用。

    僅回傳董監事清單（董事長/董事/獨立董事/監察人），不含經理人——
    經理人為另一支需「授權介接 IP」的 API（86E61A52），屬 Phase 2 範圍。
    """

    DATASET_ID = "4E5F7653-1B91-4DDC-99D5-468530FAE396"

    def get(self, request, *args, **kwargs):
        tax_id = request.GET.get('tax_id', '').strip()

        if not tax_id or len(tax_id) != 8 or not tax_id.isdigit():
            return JsonResponse({'error': '請提供正確的8位統一編號'}, status=400)

        gcis_url = (
            "https://data.gcis.nat.gov.tw/od/data/api/"
            f"{self.DATASET_ID}"
            f"?$format=json&$filter=Business_Accounting_NO%20eq%20{tax_id}&$skip=0&$top=200"
        )

        try:
            req = urllib.request.Request(gcis_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json_lib.loads(resp.read().decode('utf-8'))

            # 商工 API 在查無資料時回空陣列；非陣列代表被擋（如非授權 IP）或格式異常。
            if not isinstance(data, list):
                return JsonResponse({'error': '商工資料暫時無法取得，請稍後再試'}, status=502)

            directors = [
                {
                    'name': (d.get('Person_Name') or '').strip(),
                    'position': (d.get('Person_Position_Name') or '').strip(),
                    'entity_name': (d.get('Juristic_Person_Name') or '').strip(),
                }
                for d in data
                if (d.get('Person_Name') or '').strip()
            ]
            return JsonResponse({'success': True, 'directors': directors})

        except Exception as e:
            return JsonResponse({'error': f'查詢失敗：{str(e)}'}, status=500)
