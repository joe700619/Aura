import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class FiaApiService:
    """Service to interact with Ministry of Finance API."""
    
    BASE_URL = "https://eip.fia.gov.tw/OAI/api/businessRegistration"
    
    @classmethod
    def fetch_business_registration(cls, ban: str) -> dict:
        """
        Fetch business registration details by Business Administration Number (BAN/統一編號).
        Returns a dictionary matching the API response, or a fallback of 0/empty strings on failure.
        """
        fallback_data = {
            "ban": ban,
            "businessAddress": "",
            "headquartersBan": "",
            "businessNm": "",
            "capitalAmount": 0,
            "businessSetupDate": "",
            "businessType": "",
            "isUseInvoice": "",
            "industryCd": "",
            "industryNm": "",
            "industryCd1": "",
            "industryNm1": "",
            "industryCd2": "",
            "industryNm2": "",
            "industryCd3": "",
            "industryNm3": ""
        }
        
        if not ban or len(ban) != 8:
            return fallback_data
            
        url = f"{cls.BASE_URL}/{ban}"
        headers = {
            "accept": "application/json"
        }
        
        try:
            # Note: Many Taiwan government sites use certificates not trusted 
            # by default root bundles, so we disable SSL verification.
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            # Fia API returns raw object if success
            # If the BAN doesn't exist, it might return empty or error. Assuming it returns dictionary.
            return data if isinstance(data, dict) and data.get('ban') else fallback_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Fia API Error for BAN {ban}: {str(e)}")
            return fallback_data
        except Exception as e:
            logger.error(f"Unexpected error when fetching from Fia API for BAN {ban}: {str(e)}")
            return fallback_data

    @classmethod
    def get_industry_rates(cls, ban: str, year: int) -> dict:
        """
        Fetch the current industry code from the Ministry of Finance API,
        and cross-reference it with our local `IndustryTaxRate` table to retrieve 
        applicable rates for the given year.
        """
        from modules.bookkeeping.models import IndustryTaxRate
        
        # 1. Fetch industry registration data
        registration = cls.fetch_business_registration(ban)
        industry_cd = registration.get("industryCd", "")
        industry_nm = registration.get("industryNm", "")
        
        # 2. Setup safe default rate response
        result = {
            "industry_code": industry_cd,
            "industry_name": industry_nm,
            "book_review_profit_rate": 0,
            "net_profit_rate": 0,
            "income_standard": 0
        }
        
        if not industry_cd:
            return result
            
        # 3. Find applicable rate from master data
        # Query where applicable_year <= target year to get the most recent effective rate.
        rate_record = IndustryTaxRate.objects.filter(
            industry_code=industry_cd,
            applicable_year__lte=year
        ).order_by('-applicable_year').first()
        
        if rate_record:
            result['book_review_profit_rate'] = float(rate_record.book_review_profit_rate) if rate_record.book_review_profit_rate else 0
            result['net_profit_rate'] = float(rate_record.net_profit_rate) if rate_record.net_profit_rate else 0
            result['income_standard'] = float(rate_record.income_standard) if rate_record.income_standard else 0
            
        return result
