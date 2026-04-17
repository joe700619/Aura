import random
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, render

from ..models.payment_request import ProgressPaymentRequest
from modules.payment.models import PaymentTransaction
from modules.payment.services import ECPayService


class PublicPaymentView(TemplateView):
    template_name = 'public/payment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get('token')
        pr = get_object_or_404(ProgressPaymentRequest, token=token)
        context['pr'] = pr
        context['progress'] = pr.progress
        return context

    def post(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        pr = get_object_or_404(ProgressPaymentRequest, token=token)

        if pr.status != ProgressPaymentRequest.Status.PENDING:
            from django.http import HttpResponse
            return HttpResponse('此付款請求已完成或已取消。', status=400)

        # 1. Update Recipient Info
        pr.recipient_name  = request.POST.get('recipient_name', '')
        pr.recipient_phone = request.POST.get('recipient_phone', '')
        pr.recipient_addr  = request.POST.get('recipient_addr', '')
        pr.pickup_method   = request.POST.get('pickup_method', 'mail')
        pr.save()

        # 2. Calculate Total (amount + shipping if mail)
        total_amount = pr.amount
        has_shipping = pr.pickup_method == 'mail'
        if has_shipping:
            total_amount += 65

        # 3. Create PaymentTransaction
        random_suffix = f"{random.randint(0, 9999):04d}"
        merchant_trade_no = f"{pr.progress.registration_no}{random_suffix}"

        transaction = PaymentTransaction.objects.create(
            merchant_trade_no=merchant_trade_no,
            total_amount=total_amount,
            trade_desc=f"Service Fee for {pr.progress.company_name}",
            item_name=f"{pr.description or '委辦費用'} ({pr.progress.registration_no})",
            has_shipping=has_shipping,
            payment_type=PaymentTransaction.PaymentType.ECPAY,
            related_app='registration',
            related_model='ProgressPaymentRequest',
            related_id=str(pr.pk),
        )

        # 4. Generate ECPay Params
        service = ECPayService()
        base_url = f"{request.scheme}://{request.get_host()}"
        return_url = f"{base_url}/payment/callback/"
        client_back_url = f"{base_url}/registration/payment/{token}/"

        ecpay_data = service.generate_form_data(transaction, return_url, client_back_url)
        return render(request, 'payment/ecpay_submit.html', ecpay_data)
