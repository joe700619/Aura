from django.urls import path
from modules.bookkeeping.views import VATListView, IncomeTaxListView

urlpatterns = [
    path('vat/', VATListView.as_view(), name='vat_list'),
    path('income-tax/', IncomeTaxListView.as_view(), name='income_tax_list'),
]
