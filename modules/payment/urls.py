from django.urls import path
from .views import ECPayCallbackView, BillPublicPaymentView

app_name = 'payment'

urlpatterns = [
    path('callback/', ECPayCallbackView.as_view(), name='ecpay_callback'),
    path('bill/<str:merchant_trade_no>/', BillPublicPaymentView.as_view(), name='bill_public_payment'),
]
