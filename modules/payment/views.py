from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404, render
from .models import PaymentTransaction
from .services import ECPayService
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ECPayCallbackView(View):
    def post(self, request, *args, **kwargs):
        # 1. Get Data
        data = request.POST.dict()
        merchant_trade_no = data.get('MerchantTradeNo')
        rtn_code = data.get('RtnCode')
        rtn_msg = data.get('RtnMsg')

        logger.info(f"ECPay Callback: {data}")

        if not merchant_trade_no:
            return HttpResponse('0|No MerchantTradeNo')

        # 2. Update Transaction
        try:
            transaction = PaymentTransaction.objects.get(merchant_trade_no=merchant_trade_no)
            transaction.rtn_code = int(rtn_code)
            transaction.rtn_msg = rtn_msg
            transaction.save()

            # 3. Business Logic: Update Related Model
            if transaction.rtn_code == 1: # Success
                if transaction.related_app == 'registration' and transaction.related_model == 'Progress':
                    try:
                        Progress = apps.get_model('registration', 'Progress')
                        progress = Progress.objects.get(pk=transaction.related_id)
                        progress.payment_status = 'paid'
                        progress.save()
                    except Exception as e:
                        logger.error(f"Error updating Progress: {e}")

                if transaction.related_app == 'bookkeeping' and transaction.related_model == 'ClientBill':
                    try:
                        ClientBill = apps.get_model('bookkeeping', 'ClientBill')
                        bill = ClientBill.objects.get(pk=transaction.related_id)
                        bill.status = 'paid'
                        bill.save(update_fields=['status'])
                    except Exception as e:
                        logger.error(f"Error updating ClientBill: {e}")

            return HttpResponse('1|OK')

        except PaymentTransaction.DoesNotExist:
            return HttpResponse('0|Transaction Not Found')


class BillPublicPaymentView(View):
    """公開支付頁面：給客戶點擊，自動送出 ECPay 表單"""

    def get(self, request, merchant_trade_no):
        transaction = get_object_or_404(PaymentTransaction, merchant_trade_no=merchant_trade_no)
        service = ECPayService()
        base_url = f"{request.scheme}://{request.get_host()}"
        return_url = f"{base_url}/payment/callback/"
        client_back_url = base_url
        ecpay_data = service.generate_form_data(transaction, return_url, client_back_url)
        return render(request, 'payment/ecpay_submit.html', ecpay_data)
