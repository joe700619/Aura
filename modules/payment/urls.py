from django.urls import path
from .views import ECPayCallbackView

app_name = 'payment'

urlpatterns = [
    path('callback/', ECPayCallbackView.as_view(), name='ecpay_callback'),
]
