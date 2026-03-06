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

from modules.bookkeeping.views.business_tax import BusinessTaxListView
from modules.bookkeeping.views.business_tax_detail import BusinessTaxDetailView, AddBusinessTaxYearView, SaveTaxSettingsView
from modules.bookkeeping.views.business_tax_period import TaxFilingPeriodDetailView
from modules.bookkeeping.views.business_tax_progress import BusinessTaxProgressView
from modules.bookkeeping.views.vat_views import SendVATNotificationView, VATConfirmView
from modules.bookkeeping.views.income_tax_detail import (
    IncomeTaxClientDetailView,
    AddIncomeTaxYearView,
    SaveIncomeTaxSettingsView,
)
from modules.bookkeeping.views.provisional_tax import ProvisionalTaxDetailView
from modules.bookkeeping.views.dividend_tax import DividendTaxDetailView, ImportShareholdersView
from modules.bookkeeping.views.withholding_tax import WithholdingTaxDetailView
from modules.bookkeeping.views.income_tax_filing import IncomeTaxFilingDetailView

app_name = 'bookkeeping'

urlpatterns = [
    path('vat/', VATListView.as_view(), name='vat_list'),

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

    # 營業稅申報
    path('business-tax/', BusinessTaxListView.as_view(), name='business_tax_list'),
    path('business-tax/progress/', BusinessTaxProgressView.as_view(), name='business_tax_progress'),
    path('business-tax/<int:pk>/', BusinessTaxDetailView.as_view(), name='business_tax_detail'),
    path('business-tax/<int:pk>/add-year/', AddBusinessTaxYearView.as_view(), name='business_tax_add_year'),
    path('business-tax/<int:pk>/save-settings/', SaveTaxSettingsView.as_view(), name='business_tax_save_settings'),
    path('business-tax/<int:client_pk>/period/<int:pk>/', TaxFilingPeriodDetailView.as_view(), name='business_tax_period_detail'),
    path('business-tax/<int:client_pk>/period/<int:pk>/send-notification/', SendVATNotificationView.as_view(), name='vat_send_notification'),
    # Public (no login) VAT payment confirmation callback
    path('vat/confirm/<uuid:token>/', VATConfirmView.as_view(), name='vat_confirm'),

    # 所得稅申報
    path('income-tax/', IncomeTaxListView.as_view(), name='income_tax_list'),
    path('income-tax/<int:pk>/', IncomeTaxClientDetailView.as_view(), name='income_tax_detail'),
    path('income-tax/<int:pk>/add-year/', AddIncomeTaxYearView.as_view(), name='income_tax_add_year'),
    path('income-tax/<int:pk>/save-settings/', SaveIncomeTaxSettingsView.as_view(), name='income_tax_save_settings'),
    path('income-tax/<int:client_pk>/provisional/<int:pk>/', ProvisionalTaxDetailView.as_view(), name='provisional_tax_detail'),
    path('income-tax/<int:client_pk>/dividend/<int:pk>/', DividendTaxDetailView.as_view(), name='dividend_tax_detail'),
    path('income-tax/<int:client_pk>/dividend/<int:pk>/import-shareholders/', ImportShareholdersView.as_view(), name='import_shareholders'),
    path('income-tax/<int:client_pk>/withholding/<int:pk>/', WithholdingTaxDetailView.as_view(), name='withholding_tax_detail'),
    path('income-tax/<int:client_pk>/filing/<int:pk>/', IncomeTaxFilingDetailView.as_view(), name='income_tax_filing_detail'),
]

