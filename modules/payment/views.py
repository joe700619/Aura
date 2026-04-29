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
                if transaction.related_app == 'registration' and transaction.related_model == 'ProgressPaymentRequest':
                    try:
                        from modules.registration.models.payment_request import ProgressPaymentRequest
                        from modules.internal_accounting.models import PreCollection
                        from django.contrib.contenttypes.models import ContentType
                        import datetime

                        pr = ProgressPaymentRequest.objects.get(pk=transaction.related_id)
                        pr.status = ProgressPaymentRequest.Status.PAID
                        pr.save(update_fields=['status'])

                        # 自動建立預收款項（防止重複）
                        already = PreCollection.objects.filter(
                            transaction_no=transaction.merchant_trade_no
                        ).exists()
                        if not already:
                            progress = pr.progress
                            ct = ContentType.objects.get_for_model(progress.__class__)
                            PreCollection.objects.create(
                                date=datetime.date.today(),
                                company_name=progress.company_name,
                                unified_business_no=progress.unified_business_no or '',
                                amount=transaction.total_amount,
                                method='ecpay',
                                transaction_no=transaction.merchant_trade_no,
                                remarks=f"綠界自動收款 {pr.description or ''} 登記單號:{progress.registration_no}",
                                source_content_type=ct,
                                source_id=progress.pk,
                            )
                    except Exception as e:
                        logger.error(f"Error updating ProgressPaymentRequest: {e}")

                if transaction.related_app == 'bookkeeping' and transaction.related_model == 'ClientBill':
                    try:
                        import datetime
                        from modules.internal_accounting.models import PreCollection
                        from django.contrib.contenttypes.models import ContentType

                        ClientBill = apps.get_model('bookkeeping', 'ClientBill')
                        bill = ClientBill.objects.get(pk=transaction.related_id)
                        bill.status = 'paid'
                        bill.save(update_fields=['status'])

                        already = PreCollection.objects.filter(
                            transaction_no=transaction.merchant_trade_no
                        ).exists()
                        if not already:
                            ct = ContentType.objects.get_for_model(bill.__class__)
                            PreCollection.objects.create(
                                date=datetime.date.today(),
                                company_name=bill.client.name,
                                unified_business_no=bill.client.tax_id or '',
                                amount=transaction.total_amount,
                                method='ecpay',
                                transaction_no=transaction.merchant_trade_no,
                                remarks=f"綠界自動收款 帳單:{bill.bill_no}",
                                source_content_type=ct,
                                source_id=bill.pk,
                            )
                    except Exception as e:
                        logger.error(f"Error updating ClientBill: {e}")

                if transaction.related_app == 'internal_accounting' and transaction.related_model == 'Receivable':
                    try:
                        from modules.internal_accounting.models import Receivable, Collection
                        from modules.internal_accounting.services import AccountingService
                        import datetime

                        receivable = Receivable.objects.get(pk=transaction.related_id)

                        # 防止重複建立（同一交易號已有綠界收款單）
                        already = Collection.objects.filter(
                            receivable=receivable,
                            remarks__contains=transaction.merchant_trade_no
                        ).exists()
                        if not already:
                            collection = Collection.objects.create(
                                receivable=receivable,
                                date=datetime.date.today(),
                                method='ecpay',
                                amount=transaction.total_amount,
                                tax=0,
                                fee=0,
                                allowance=0,
                                remarks=f"綠界自動收款 交易編號:{transaction.merchant_trade_no}",
                                auto_created=True,
                            )
                            # 自動過帳（無使用者，系統操作）
                            try:
                                AccountingService.post_collection(collection, user=None)
                            except Exception as post_err:
                                logger.error(f"ECPay auto post_collection failed: {post_err}")
                    except Exception as e:
                        logger.error(f"Error creating Collection from ECPay: {e}")

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
