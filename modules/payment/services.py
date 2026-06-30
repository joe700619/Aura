import hashlib
import urllib.parse
from datetime import datetime
from django.conf import settings
from django.utils import timezone
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
        """
        依綠界 CheckMacValue 規格產生檢查碼（EncryptType=1 → SHA256）。
        邏輯對齊官方 ECPay Python SDK，步驟：
          1. 排除 CheckMacValue 本身，key 依「忽略大小寫」排序
          2. 串成 HashKey=...&k=v&...&HashIV=...
          3. quote_plus（空白 → +）後轉小寫
          4. 還原 .NET HttpUtility.UrlEncode 不會編碼的字元
          5. SHA256 後轉大寫
        """
        # 1. 排序（忽略大小寫，且不納入 CheckMacValue）
        items = sorted(
            ((k, v) for k, v in params.items() if k != 'CheckMacValue'),
            key=lambda x: x[0].lower(),
        )

        # 2. 串接
        raw_str = f"HashKey={self.hash_key}"
        for key, value in items:
            raw_str += f"&{key}={value}"
        raw_str += f"&HashIV={self.hash_iv}"

        # 3. URL encode（quote_plus：空白 → '+'）後轉小寫
        encoded_str = urllib.parse.quote_plus(raw_str).lower()

        # 4. 還原 .NET HttpUtility.UrlEncode 與 Python 編碼差異的字元
        replacements = {
            '%2d': '-', '%5f': '_', '%2e': '.', '%21': '!',
            '%2a': '*', '%28': '(', '%29': ')', '%20': '+',
        }
        for src, dst in replacements.items():
            encoded_str = encoded_str.replace(src, dst)

        # 5. SHA256 → 大寫
        return hashlib.sha256(encoded_str.encode('utf-8')).hexdigest().upper()

    def generate_form_data(self, transaction, return_url, client_back_url):
        """
        Generates the form data required to post to ECPay.
        """
        # trade_date 存的是 UTC（USE_TZ=True），轉成台北時間再送給綠界
        trade_date_str = timezone.localtime(transaction.trade_date).strftime('%Y/%m/%d %H:%M:%S')
        
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

        # Business Logic: 依金額決定可用付款方式
        #   - 金額 <= 1000：全部管道都開（ChoosePayment='ALL'，不排除）
        #   - 金額 >= 1001：只開 WebATM / ATM / CVS / BARCODE，
        #                   其餘（Credit、ApplePay、TWQR、BNPL）用 IgnorePayment 排除
        # ECPay 的 IgnorePayment 以 '#' 分隔，例如 Credit#ApplePay#TWQR#BNPL
        if transaction.total_amount > 1000:
            params['IgnorePayment'] = 'Credit#ApplePay#TWQR#BNPL'

        # Generate CheckMacValue
        params['CheckMacValue'] = self.generate_check_max_value(params)
        
        return {
            'action_url': self.action_url,
            'params': params
        }
