import logging
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from core.services.fia_api import FiaApiService

logger = logging.getLogger(__name__)

class FetchIndustryRatesApiView(LoginRequiredMixin, View):
    """
    API endpoint to fetch industry rates from Ministry of Finance based on BAN and year.
    Used by frontend forms to auto-populate rate fields.
    """
    def get(self, request, *args, **kwargs):
        tax_id = request.GET.get('tax_id', '').strip()
        year_str = request.GET.get('year', '').strip()
        
        if not tax_id:
            return JsonResponse({'error': 'Missing tax_id (統一編號)'}, status=400)
            
        try:
            year = int(year_str)
        except ValueError:
            return JsonResponse({'error': 'Invalid year format'}, status=400)
            
        try:
            rates_data = FiaApiService.get_industry_rates(tax_id, year)
            return JsonResponse(rates_data)
        except Exception as e:
            logger.error(f"Error fetching FIA rates for {tax_id}: {str(e)}")
            return JsonResponse({'error': 'Internal server error while fetching rates'}, status=500)
