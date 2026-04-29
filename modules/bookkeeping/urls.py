from django.urls import path
from modules.bookkeeping.views import VATListView, IncomeTaxListView, IndustryTaxRateListView
from modules.bookkeeping.views.income_tax import IncomeTaxProgressView
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
from modules.bookkeeping.views.vat_views import SendVATNotificationView, VATConfirmView, CheckOutstandingReceivablesAPI
from modules.bookkeeping.views.progress_views import (
    ProgressListView, ProgressDetailView, AddProgressYearView, ProgressPeriodDetailView,
    ProgressTrackerView, RunExpertSystemView, SaveExpertRuleSettingsView
)
from modules.bookkeeping.views.income_tax_detail import (
    IncomeTaxClientDetailView,
    AddIncomeTaxYearView,
    SaveIncomeTaxSettingsView,
)
from modules.bookkeeping.views.provisional_tax import ProvisionalTaxDetailView, SendProvisionalTaxNotificationView
from modules.bookkeeping.views.dividend_tax import DividendTaxDetailView, ImportShareholdersView
from modules.bookkeeping.views.withholding_tax import WithholdingTaxDetailView, SendWithholdingTaxNotificationView
from modules.bookkeeping.views.income_tax_filing import IncomeTaxFilingDetailView
from modules.bookkeeping.views.income_tax_media import (
    IncomeTaxMediaDetailView, IncomeTaxMediaUploadView, IncomeTaxMediaSlideoverAPI,
)
from modules.bookkeeping.views.bill_views import (
    ClientBillListView, ClientBillCreateView,
    ClientBillUpdateView, ClientBillDeleteView, ClientBillTransferView,
    FetchUnbilledAdvancePaymentsView, BookkeepingClientSearchView,
    GenerateBillPaymentLinkView,
    BillBatchPreviewView, BillBatchGenerateView,
)
from modules.bookkeeping.views.corporate_tax import CorporateTaxDraftAPIView, ImportCorporateTaxExcelAPIView
from modules.bookkeeping.views.api_rates import FetchIndustryRatesApiView
from modules.bookkeeping.views.api_progress_summary import ProgressSummaryAPIView
from modules.bookkeeping.views.business_registration import (
    BusinessRegistrationListView,
    BusinessRegistrationUpdateView,
)
from modules.bookkeeping.views.service_remuneration_tax_rate import (
    ServiceRemunerationTaxRateListView,
    ServiceRemunerationTaxRateCreateView,
    ServiceRemunerationTaxRateUpdateView,
    ServiceRemunerationTaxRateDeleteView,
    NHIConfigUpdateView,
)

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
    path('business-tax/<int:client_pk>/check-receivables/', CheckOutstandingReceivablesAPI.as_view(), name='api_check_receivables'),
    # Public (no login) VAT payment confirmation callback
    path('vat/confirm/<uuid:token>/', VATConfirmView.as_view(), name='vat_confirm'),

    # 記帳進度表
    path('progress/', ProgressListView.as_view(), name='progress_list'),
    path('progress/tracker/', ProgressTrackerView.as_view(), name='progress_tracker'),
    path('progress/<int:pk>/', ProgressDetailView.as_view(), name='progress_detail'),
    path('progress/<int:client_pk>/save-expert-settings/', SaveExpertRuleSettingsView.as_view(), name='progress_save_expert_settings'),
    path('progress/<int:pk>/add-year/', AddProgressYearView.as_view(), name='progress_add_year'),
    path('progress/<int:client_pk>/period/<int:pk>/', ProgressPeriodDetailView.as_view(), name='progress_period_detail'),
    path('progress/<int:client_pk>/period/<int:pk>/run-expert/', RunExpertSystemView.as_view(), name='progress_run_expert'),

    # 所得稅申報
    path('income-tax/', IncomeTaxListView.as_view(), name='income_tax_list'),
    path('income-tax/progress/', IncomeTaxProgressView.as_view(), name='income_tax_progress'),
    path('income-tax/<int:pk>/', IncomeTaxClientDetailView.as_view(), name='income_tax_detail'),
    path('income-tax/<int:pk>/add-year/', AddIncomeTaxYearView.as_view(), name='income_tax_add_year'),
    path('income-tax/<int:pk>/save-settings/', SaveIncomeTaxSettingsView.as_view(), name='income_tax_save_settings'),
    path('income-tax/<int:client_pk>/provisional/<int:pk>/', ProvisionalTaxDetailView.as_view(), name='provisional_tax_detail'),
    path('income-tax/<int:client_pk>/provisional/<int:pk>/send-notification/', SendProvisionalTaxNotificationView.as_view(), name='provisional_tax_send_notification'),
    path('income-tax/<int:client_pk>/dividend/<int:pk>/', DividendTaxDetailView.as_view(), name='dividend_tax_detail'),
    path('income-tax/<int:client_pk>/dividend/<int:pk>/import-shareholders/', ImportShareholdersView.as_view(), name='import_shareholders'),
    path('income-tax/<int:client_pk>/withholding/<int:pk>/', WithholdingTaxDetailView.as_view(), name='withholding_tax_detail'),
    path('income-tax/<int:client_pk>/withholding/<int:pk>/send-notification/', SendWithholdingTaxNotificationView.as_view(), name='withholding_tax_send_notification'),
    path('income-tax/<int:client_pk>/filing/<int:pk>/', IncomeTaxFilingDetailView.as_view(), name='income_tax_filing_detail'),

    # 申報書媒體檔
    path('income-tax/<int:client_pk>/media/<int:pk>/', IncomeTaxMediaDetailView.as_view(), name='income_tax_media_detail'),
    path('income-tax/<int:client_pk>/media/<int:pk>/upload/', IncomeTaxMediaUploadView.as_view(), name='income_tax_media_upload'),

    # 商工登記
    path('business-registration/', BusinessRegistrationListView.as_view(), name='business_registration_list'),
    path('business-registration/<int:pk>/edit/', BusinessRegistrationUpdateView.as_view(), name='business_registration_update'),

    # 勞務報酬稅率設定
    path('service-remuneration-tax-rates/', ServiceRemunerationTaxRateListView.as_view(), name='service_remuneration_tax_rate_list'),
    path('service-remuneration-tax-rates/add/', ServiceRemunerationTaxRateCreateView.as_view(), name='service_remuneration_tax_rate_create'),
    path('service-remuneration-tax-rates/<int:pk>/edit/', ServiceRemunerationTaxRateUpdateView.as_view(), name='service_remuneration_tax_rate_update'),
    path('service-remuneration-tax-rates/<int:pk>/delete/', ServiceRemunerationTaxRateDeleteView.as_view(), name='service_remuneration_tax_rate_delete'),
    path('service-remuneration-tax-rates/nhi-config/', NHIConfigUpdateView.as_view(), name='nhi_config_update'),

    # 客戶帳單系統
    path('bills/', ClientBillListView.as_view(), name='bill_list'),
    path('bills/batch-preview/', BillBatchPreviewView.as_view(), name='bill_batch_preview'),
    path('bills/batch-generate/', BillBatchGenerateView.as_view(), name='bill_batch_generate'),
    path('bills/add/', ClientBillCreateView.as_view(), name='bill_create'),
    path('bills/<int:pk>/edit/', ClientBillUpdateView.as_view(), name='bill_update'),
    path('bills/<int:pk>/delete/', ClientBillDeleteView.as_view(), name='bill_delete'),
    path('bills/<int:pk>/transfer/', ClientBillTransferView.as_view(), name='bill_transfer'),
    path('bills/<int:pk>/generate-payment-link/', GenerateBillPaymentLinkView.as_view(), name='bill_generate_payment_link'),
    
    # API
    path('api/unbilled-advance-payments/<int:client_pk>/', FetchUnbilledAdvancePaymentsView.as_view(), name='api_unbilled_advance_payments'),
    path('api/clients/search/', BookkeepingClientSearchView.as_view(), name='api_client_search'),
    path('api/corporate-tax/<int:year_id>/', CorporateTaxDraftAPIView.as_view(), name='api_corporate_tax_draft'),
    path('api/corporate-tax/<int:year_id>/import/', ImportCorporateTaxExcelAPIView.as_view(), name='api_corporate_tax_import'),
    path('api/industry-rates/fetch/', FetchIndustryRatesApiView.as_view(), name='api_industry_rates_fetch'),
    path('api/income-tax/<int:client_pk>/media-data/', IncomeTaxMediaSlideoverAPI.as_view(), name='api_income_tax_media_data'),
    path('api/progress-summary/', ProgressSummaryAPIView.as_view(), name='api_progress_summary'),

    # Industry Tax Rates (Master Data)
    path('industry-tax-rates/', IndustryTaxRateListView.as_view(), name='industry_tax_rate_list'),
]
