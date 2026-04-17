from django.urls import path
from .views import (
    VoucherListView, VoucherCreateView, VoucherUpdateView, VoucherDeleteView,
    AccountListView, AccountCreateView, AccountUpdateView, AccountDeleteView,
    ReceivableListView, ReceivableCreateView, ReceivableUpdateView, ReceivableDeleteView
)
from .views.receivable import GenerateReceivablePaymentLinkView
from .views.collection import (
    CollectionListView, CollectionCreateView, CollectionUpdateView, CollectionDeleteView,
    search_receivables, search_receivables_json, post_collection_view
)
from .views.pre_collection import (
    PreCollectionListView, PreCollectionUpdateView, PreCollectionDeleteView,
    match_pre_collection_view
)
from .views.fixed_asset_views import create_fixed_asset_api, FixedAssetListView, FixedAssetCreateView, FixedAssetUpdateView, FixedAssetDeleteView
from .views.fixed_asset_report import FixedAssetReportView
from .views.report import JournalListView, GeneralLedgerListView, IncomeStatementView, BalanceSheetView, SubsidiaryLedgerView
from .views.withholding_tax import WithholdingTaxSummaryView, WithholdingTaxExportView, WithholdingTaxSendEmailView, WithholdingTaxDataView
from .views.fee_apportion_report import FeeApportionReportView, FeeApportionExportView
from .views.period import AccountingPeriodListView, toggle_period_status, close_year_action, run_depreciation_action

app_name = 'internal_accounting'

urlpatterns = [
    # Voucher
    path('vouchers/', VoucherListView.as_view(), name='voucher_list'),
    path('vouchers/create/', VoucherCreateView.as_view(), name='voucher_create'),
    path('vouchers/<int:pk>/edit/', VoucherUpdateView.as_view(), name='voucher_edit'),
    path('vouchers/<int:pk>/delete/', VoucherDeleteView.as_view(), name='voucher_delete'),
    
    # Account List (for reference or future management)
    path('accounts/', AccountListView.as_view(), name='account_list'),
    path('accounts/create/', AccountCreateView.as_view(), name='account_create'),
    path('accounts/<str:pk>/edit/', AccountUpdateView.as_view(), name='account_edit'),
    path('accounts/<str:pk>/delete/', AccountDeleteView.as_view(), name='account_delete'),

    # Receivable (AR)
    path('receivables/', ReceivableListView.as_view(), name='receivable_list'),
    path('receivables/create/', ReceivableCreateView.as_view(), name='receivable_create'),
    path('receivables/<int:pk>/edit/', ReceivableUpdateView.as_view(), name='receivable_edit'),
    path('receivables/<int:pk>/delete/', ReceivableDeleteView.as_view(), name='receivable_delete'),
    path('receivables/<int:pk>/generate-payment-link/', GenerateReceivablePaymentLinkView.as_view(), name='receivable_generate_payment_link'),
    
    # Collection (Payment Management)
    path('collections/', CollectionListView.as_view(), name='collection_list'),
    path('collections/create/', CollectionCreateView.as_view(), name='collection_create'),
    path('collections/<int:pk>/edit/', CollectionUpdateView.as_view(), name='collection_edit'),
    path('collections/<int:pk>/delete/', CollectionDeleteView.as_view(), name='collection_delete'),
    path('collections/<int:pk>/post/', post_collection_view, name='collection_post'),

    # PreCollection (預收款項)
    path('pre-collections/', PreCollectionListView.as_view(), name='pre_collection_list'),
    path('pre-collections/<int:pk>/edit/', PreCollectionUpdateView.as_view(), name='pre_collection_edit'),
    path('pre-collections/<int:pk>/delete/', PreCollectionDeleteView.as_view(), name='pre_collection_delete'),
    path('pre-collections/<int:pk>/match/', match_pre_collection_view, name='pre_collection_match'),
    
    # APIs
    path('api/receivables/search/', search_receivables, name='api_receivable_search'),
    path('api/receivables/search-json/', search_receivables_json, name='api_receivable_search_json'),
    path('api/fixed-asset/create/', create_fixed_asset_api, name='create_fixed_asset_api'),
    
    # Fixed Assets
    path('fixed-assets/', FixedAssetListView.as_view(), name='fixed_asset_list'),
    path('fixed-assets/create/', FixedAssetCreateView.as_view(), name='fixed_asset_create'),
    path('fixed-assets/<int:pk>/edit/', FixedAssetUpdateView.as_view(), name='fixed_asset_update'),
    path('fixed-assets/<int:pk>/delete/', FixedAssetDeleteView.as_view(), name='fixed_asset_delete'),
    path('fixed-assets/report/', FixedAssetReportView.as_view(), name='fixed_asset_report'),
    
    # Reports
    path('reports/journal/', JournalListView.as_view(), name='report_journal'),
    path('reports/general-ledger/', GeneralLedgerListView.as_view(), name='report_general_ledger'),
    path('reports/subsidiary-ledger/', SubsidiaryLedgerView.as_view(), name='report_subsidiary_ledger'),
    path('reports/income-statement/', IncomeStatementView.as_view(), name='report_income_statement'),
    path('reports/balance-sheet/', BalanceSheetView.as_view(), name='report_balance_sheet'),
    path('reports/withholding-tax/', WithholdingTaxSummaryView.as_view(), name='report_withholding_tax'),
    path('reports/withholding-tax/export/', WithholdingTaxExportView.as_view(), name='report_withholding_tax_export'),
    path('reports/withholding-tax/send-email/', WithholdingTaxSendEmailView.as_view(), name='report_withholding_tax_send_email'),
    path('reports/withholding-tax/data/', WithholdingTaxDataView.as_view(), name='report_withholding_tax_data'),
    
    # Fee Apportionment Report
    path('reports/fee-apportion/', FeeApportionReportView.as_view(), name='report_fee_apportion'),
    path('reports/fee-apportion/export/', FeeApportionExportView.as_view(), name='report_fee_apportion_export'),

    # Accounting Periods
    path('periods/', AccountingPeriodListView.as_view(), name='period_list'),
    path('periods/<int:pk>/toggle/', toggle_period_status, name='toggle_period_status'),
    path('periods/close-year/', close_year_action, name='close_year_action'),
    path('periods/depreciation/', run_depreciation_action, name='run_depreciation_action'),
]
