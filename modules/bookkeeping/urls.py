from django.urls import path
from modules.bookkeeping.views import VATListView, IncomeTaxListView
from modules.bookkeeping.views.bookkeeping_client import (
    BookkeepingClientListView,
    BookkeepingClientCreateView,
    BookkeepingClientUpdateView,
    BookkeepingClientDeleteView,
)
from modules.bookkeeping.views.group_invoice_report import (
    GroupInvoiceReportView,
    GroupInvoiceExportView,
)

from modules.bookkeeping.views.convenience_bag import (
    ConvenienceBagListView,
    ConvenienceBagUpdateView,
)

app_name = 'bookkeeping'

urlpatterns = [
    path('vat/', VATListView.as_view(), name='vat_list'),
    path('income-tax/', IncomeTaxListView.as_view(), name='income_tax_list'),

    # 記帳客戶基本資料
    path('clients/', BookkeepingClientListView.as_view(), name='client_list'),
    path('clients/add/', BookkeepingClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/edit/', BookkeepingClientUpdateView.as_view(), name='client_update'),
    path('clients/<int:pk>/delete/', BookkeepingClientDeleteView.as_view(), name='client_delete'),

    # 統購發票查詢
    path('group-invoice-report/', GroupInvoiceReportView.as_view(), name='group_invoice_report'),
    path('group-invoice-report/export/', GroupInvoiceExportView.as_view(), name='group_invoice_export'),

    # 7-11 便利袋管理
    path('convenience-bags/', ConvenienceBagListView.as_view(), name='convenience_bag_list'),
    path('convenience-bags/<int:pk>/edit/', ConvenienceBagUpdateView.as_view(), name='convenience_bag_update'),
]
