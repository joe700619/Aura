from django.urls import path
from .views import (
    VoucherListView, VoucherCreateView, VoucherUpdateView, VoucherDeleteView,
    AccountListView, AccountCreateView, AccountUpdateView, AccountDeleteView,
    ReceivableListView, ReceivableCreateView, ReceivableUpdateView, ReceivableDeleteView
)
from .views.collection import (
    CollectionListView, CollectionCreateView, CollectionUpdateView, CollectionDeleteView,
    search_receivables
)
from .views.report import JournalListView, GeneralLedgerListView, IncomeStatementView, BalanceSheetView, SubsidiaryLedgerView
from .views.withholding_tax import WithholdingTaxSummaryView, WithholdingTaxExportView, WithholdingTaxSendEmailView
from .views.fee_apportion_report import FeeApportionReportView, FeeApportionExportView

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
    
    # Collection (Payment Management)
    path('collections/', CollectionListView.as_view(), name='collection_list'),
    path('collections/create/', CollectionCreateView.as_view(), name='collection_create'),
    path('collections/<int:pk>/edit/', CollectionUpdateView.as_view(), name='collection_edit'),
    path('collections/<int:pk>/delete/', CollectionDeleteView.as_view(), name='collection_delete'),
    
    # APIs
    path('api/receivables/search/', search_receivables, name='api_receivable_search'),
    
    # Reports
    path('reports/journal/', JournalListView.as_view(), name='report_journal'),
    path('reports/general-ledger/', GeneralLedgerListView.as_view(), name='report_general_ledger'),
    path('reports/subsidiary-ledger/', SubsidiaryLedgerView.as_view(), name='report_subsidiary_ledger'),
    path('reports/income-statement/', IncomeStatementView.as_view(), name='report_income_statement'),
    path('reports/balance-sheet/', BalanceSheetView.as_view(), name='report_balance_sheet'),
    path('reports/withholding-tax/', WithholdingTaxSummaryView.as_view(), name='report_withholding_tax'),
    path('reports/withholding-tax/export/', WithholdingTaxExportView.as_view(), name='report_withholding_tax_export'),
    path('reports/withholding-tax/send-email/', WithholdingTaxSendEmailView.as_view(), name='report_withholding_tax_send_email'),
    
    # Fee Apportionment Report
    path('reports/fee-apportion/', FeeApportionReportView.as_view(), name='report_fee_apportion'),
    path('reports/fee-apportion/export/', FeeApportionExportView.as_view(), name='report_fee_apportion_export'),
]
