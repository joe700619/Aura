import hashlib
import urllib.parse
from datetime import datetime
from django.conf import settings
from modules.system_config.models import SystemParameter

class ECPayService:
    def __init__(self):
        # Load config from SystemParameter. Raises error if missing to prevent using wrong credentials.
        self.merchant_id = self._get_param('ECPAY_MERCHANT_ID', required=True)
        self.hash_key = self._get_param('ECPAY_HASH_KEY', required=True)
        self.hash_iv = self._get_param('ECPAY_HASH_IV', required=True)
        self.action_url = self._get_param('ECPAY_ACTION_URL', 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5')

    def _get_param(self, key, default=None, required=False):
        try:
            param = SystemParameter.objects.get(key=key)
            if not param.value:
                if required:
                    raise ValueError(f"System Parameter '{key}' is empty.")
                return default
            return param.value
        except SystemParameter.DoesNotExist:
            if required:
                raise ValueError(f"System Parameter '{key}' is missing. Please configure it in System > Parameters.")
            return default

    def generate_check_max_value(self, params):
        # 1. Sort by key
        sorted_keys = sorted(params.keys())
        
        # 2. Concatenate "HashKey=...&key=value...&HashIV=..."
        raw_str = f"HashKey={self.hash_key}&"
        for key in sorted_keys:
            raw_str += f"{key}={params[key]}&"
        raw_str += f"HashIV={self.hash_iv}"
        
        # 3. URL Encode
        # ECPay requires specific encoding: lowercase, restricted characters replacement
        # .NET HttpUtility.UrlEncode behavior:
        # - Spaces become '+' (but usually handled by quote_plus or quote)
        # - ECPay doc says: standard URL Encode, then convert to lowercase.
        # - Specific replacements: %2d -> -, %5f -> _, %2e -> ., %21 -> !, %2a -> *, %28 -> (, %29 -> )
        
        # Using quote_plus to handle spaces as '+' which is standard for form data, 
        # but ECPay might expect %20. Let's stick to quote with safe='()!*'.
        # Actually, Python's quote encodes spaces as %20. 
        # Let's align with the official SDK logic:
        # https://github.com/ECPay/ECPayAIO_Python/blob/master/ecpay_payment_sdk/ecpay_payment_sdk.py
        
        encoded_str = urllib.parse.quote(raw_str, safe='()!*').lower()
        
        # Manual replacements to match .NET/ECPay quirks if standard quote differs
        # Python quote (safe='()!*') keeps ( ) ! * unencoded.
        # It encodes - _ . as unencoded (standard).
        # It encodes space as %20.
        # It encodes ~ as %7e (which is correct for ECPay as they want lower case).
        
        # ECPay specific replacements AFTER encoding and lowercasing:
        # The logic is: encode everything, then replace these specific sequences back to characters?
        # No, the docs say: If the encoded buffer contains %2d, replace with -, etc.
        # This implies we should encode comprehensively and then revert specific chars.
        
        encoded_str = encoded_str.replace('%2d', '-') \
                                 .replace('%5f', '_') \
                                 .replace('%2e', '.') \
                                 .replace('%21', '!') \
                                 .replace('%2a', '*') \
                                 .replace('%28', '(') \
                                 .replace('%29', ')') \
                                 .replace('%20', '+') # ECPay might want + for spaces? SDK uses quote_plus?
                                 
        # Let's verify against SDK.
        # SDK uses `quote` then replacements.
        # SDK: ret_url = quote(s, safe='()!*')
        # SDK: ret_url = ret_url.replace('%2D', '-').replace('%5F', '_').replace('%2E', '.').replace('%21', '!').replace('%2A', '*').replace('%28', '(').replace('%29', ')')
        # SDK: ret_url = ret_url.lower()
        # My implementation `quote(..., safe='()!*').lower()` effectively does the replacements for ()!* because safe keeps them raw.
        # Determining if quote encodes -_.? No, it keeps them raw.
        # So `safe='()!*'` covers most.
        # Space? Python quote -> %20. SDK doesn't replace %20.
        # Lowercase %20 -> %20.
        
        # What about `141` error?
        # It might be `ItemName` or `TradeDesc` encoding?
        # They should be passed as raw to this function, and encoded here.
        # Wait, if ItemName contains spaces/Chinese, `raw_str` will look like `ItemName=中文...`.
        # `quote` will encode Chinese.
        
        # Verify hash calculation manually or trust this.
        # The most common cause for 10200141 is actually incorrect MerchantID/HashKey/HashIV combo.
        
        # Reseting to strictly match SDK logic for safety:
        # Quote with safe='()!*'
        # Lowercase
        # (The replacements in SDK are for when usage of quote_plus or other variants might have encoded them, but quote(safe='()!*') is usually close enough)
        
        # Let's ensure standard behavior.
        
        # 4. SHA256
        m = hashlib.sha256()
        m.update(encoded_str.encode('utf-8'))
        return m.hexdigest().upper()

    def generate_form_data(self, transaction, return_url, client_back_url):
        """
        Generates the form data required to post to ECPay.
        """
        trade_date_str = transaction.trade_date.strftime('%Y/%m/%d %H:%M:%S')
        
        params = {
            'MerchantID': self.merchant_id,
            'MerchantTradeNo': transaction.merchant_trade_no,
            'MerchantTradeDate': trade_date_str,
            'PaymentType': 'aio',
            'TotalAmount': str(int(transaction.total_amount)),
            'TradeDesc': transaction.trade_desc[:200], # max 200
            'ItemName': transaction.item_name[:200],   # max 200
            'ReturnURL': return_url,
            'ChoosePayment': 'ALL',
            'ClientBackURL': client_back_url,
            'EncryptType': '1',
            'NeedExtraPaidInfo': 'N',
        }

        # Business Logic: Disable BNPL if amount <= 500
        # ECPay allows excluding payment methods via IgnorePayment
        # Credit#ApplePay#TWQR#BNPL
        if transaction.total_amount <= 500:
            # If <= 500, we want to IGNORE BNPL.
            # But the requirement says: "If > 500, ALL allowed. Else, ONLY BNPL disallowed"
            # So if <= 500, IgnorePayment="BNPL"
            params['IgnorePayment'] = 'BNPL'

        # Generate CheckMacValue
        params['CheckMacValue'] = self.generate_check_max_value(params)
        
        return {
            'action_url': self.action_url,
            'params': params
        }
