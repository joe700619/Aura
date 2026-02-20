from django.views.generic import TemplateView, View
from django.shortcuts import get_object_or_404, render
from ..models.progress import Progress
from modules.payment.models import PaymentTransaction
from modules.payment.services import ECPayService
import random
from django.urls import reverse

class PublicPaymentView(TemplateView):
    template_name = 'public/payment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get('token')
        progress = get_object_or_404(Progress, payment_token=token)
        context['progress'] = progress
        
        # Serialize quotation_data for frontend
        quotation_data = progress.quotation_data or []
        import json
        context['quotation_data_json'] = json.dumps(quotation_data)
        
        return context

    def post(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        progress = get_object_or_404(Progress, payment_token=token)

        # 1. Update Recipient Info
        progress.recipient_name = request.POST.get('recipient_name')
        progress.recipient_phone = request.POST.get('recipient_phone')
        progress.recipient_addr = request.POST.get('recipient_addr')
        progress.pickup_method = request.POST.get('pickup_method')
        progress.save()

        # 2. Calculate Total
        total_amount = sum(int(item.get('amount', 0)) for item in progress.quotation_data)
        has_shipping = False
        if progress.pickup_method == 'mail':
            total_amount += 65
            has_shipping = True

        # 3. Create Transaction
        # Format: RO20230101001 + 4 random digits
        random_suffix = f"{random.randint(0, 9999):04d}"
        merchant_trade_no = f"{progress.registration_no}{random_suffix}"
        
        transaction = PaymentTransaction.objects.create(
            merchant_trade_no=merchant_trade_no,
            total_amount=total_amount,
            trade_desc=f"Service Fee for {progress.company_name}",
            item_name=f"委辦費用 ({progress.registration_no})",
            has_shipping=has_shipping,
            payment_type=PaymentTransaction.PaymentType.ECPAY,
            related_app='registration',
            related_model='Progress',
            related_id=str(progress.pk)
        )

        # 4. Generate ECPay Params
        service = ECPayService()
        # TODO: Define return URL and client back URL
        # For now, using homepage or a specific success page
        base_url = f"{request.scheme}://{request.get_host()}"
        return_url = f"{base_url}/payment/callback/" 
        client_back_url = f"{base_url}/registration/payment/{token}/" # Back to form for now or specific thank you page

        ecpay_data = service.generate_form_data(transaction, return_url, client_back_url)

        return render(request, 'payment/ecpay_submit.html', ecpay_data)
