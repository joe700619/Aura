from django.urls import path
from .views.progress import (
    ProgressListView,
    ProgressCreateView,
    ProgressUpdateView,
    ProgressDeleteView,
    PaymentLinkGenerateView,
    ProgressTransferToARView,
)
from .views.client_assessment import (
    ClientAssessmentListView,
    ClientAssessmentCreateView,
    ClientAssessmentUpdateView,
    ClientAssessmentUpdateView,
    ClientAssessmentDeleteView,
    client_assessment_submit_approval,
    client_assessment_approve,
    client_assessment_reject,
    client_assessment_return,
    client_assessment_cancel_approval,
)
from .views import api
from .views.public_payment import PublicPaymentView
from .views import case_assessment
from .views.shareholder import (
    ShareholderListView,
    ShareholderCreateView,
    ShareholderUpdateView,
    ShareholderDeleteView,
)
from .views.equity_transaction import (
    EquityTransactionListView,
    EquityTransactionCreateView,
    EquityTransactionUpdateView,
    EquityTransactionDeleteView,
)
from .views.shareholder_register import (
    ShareholderRegisterListView,
    ShareholderRegisterCreateView,
    ShareholderRegisterUpdateView,
    ShareholderRegisterDeleteView,
)
from .views.company_filing import (
    CompanyFilingListView,
    CompanyFilingCreateView,
    CompanyFilingUpdateView,
    CompanyFilingDeleteView,
)
from .views.filing_history import (
    FilingHistoryUpdateView,
    FilingHistoryDeleteView,
)
from .views.vat_entity_change import (
    VATEntityChangeListView,
    VATEntityChangeCreateView,
    VATEntityChangeUpdateView,
    VATEntityChangeDeleteView,
)

app_name = 'registration'

urlpatterns = [
    path('progress/', ProgressListView.as_view(), name='progress_list'),
    path('progress/add/', ProgressCreateView.as_view(), name='progress_create'),
    path('progress/<int:pk>/edit/', ProgressUpdateView.as_view(), name='progress_edit'),
    path('progress/<int:pk>/delete/', ProgressDeleteView.as_view(), name='progress_delete'),
    path('progress/<int:pk>/payment-link/', PaymentLinkGenerateView.as_view(), name='progress_generate_link'),
    path('progress/<int:pk>/transfer-ar/', ProgressTransferToARView.as_view(), name='progress_transfer_ar'),
    path('payment/<uuid:token>/', PublicPaymentView.as_view(), name='public_payment'),
    
    # Client Assessment
    path('client-assessments/', ClientAssessmentListView.as_view(), name='client_assessment_list'),
    path('client-assessments/add/', ClientAssessmentCreateView.as_view(), name='client_assessment_create'),
    path('client-assessments/<int:pk>/edit/', ClientAssessmentUpdateView.as_view(), name='client_assessment_update'),
    path('client-assessments/<int:pk>/delete/', ClientAssessmentDeleteView.as_view(), name='client_assessment_delete'),
    
    # Client Assessment Approval Actions
    path('client-assessments/<int:pk>/submit-approval/', client_assessment_submit_approval, name='clientassessment_submit_approval'),
    path('client-assessments/<int:pk>/approve/', client_assessment_approve, name='clientassessment_approve'),
    path('client-assessments/<int:pk>/reject/', client_assessment_reject, name='clientassessment_reject'),
    path('client-assessments/<int:pk>/return/', client_assessment_return, name='clientassessment_return'),
    path('client-assessments/<int:pk>/cancel-approval/', client_assessment_cancel_approval, name='clientassessment_cancel_approval'),
    # Case Assessment URLs
    path('case-assessments/', case_assessment.CaseAssessmentListView.as_view(), name='case_assessment_list'),
    path('case-assessments/create/', case_assessment.CaseAssessmentCreateView.as_view(), name='case_assessment_create'),
    path('case-assessments/<int:pk>/update/', case_assessment.CaseAssessmentUpdateView.as_view(), name='case_assessment_update'),
    path('case-assessments/<int:pk>/delete/', case_assessment.CaseAssessmentDeleteView.as_view(), name='case_assessment_delete'),
    
    # Case Assessment Approval Actions
    path('case-assessments/<int:pk>/submit-approval/', case_assessment.case_assessment_submit_approval, name='caseassessment_submit_approval'),
    path('case-assessments/<int:pk>/approve/', case_assessment.case_assessment_approve, name='caseassessment_approve'),
    path('case-assessments/<int:pk>/reject/', case_assessment.case_assessment_reject, name='caseassessment_reject'),
    path('case-assessments/<int:pk>/return/', case_assessment.case_assessment_return, name='caseassessment_return'),
    path('case-assessments/<int:pk>/cancel-approval/', case_assessment.case_assessment_cancel_approval, name='caseassessment_cancel_approval'),
    
    # API
    path('api/client-assessment-search/', api.ClientAssessmentSearchApiView.as_view(), name='client_assessment_search'),
    path('api/progress-search/', api.ProgressSearchApiView.as_view(), name='progress_search'),
    path('api/shareholder-search/', api.ShareholderSearchApiView.as_view(), name='shareholder_search'),
    path('api/shareholder-register-search/', api.ShareholderRegisterSearchApiView.as_view(), name='shareholder_register_search'),
    path('api/filing-history/<int:pk>/toggle-status/', api.ToggleFilingHistoryStatusApiView.as_view(), name='filing_history_toggle_status'),

    # Shareholder
    path('shareholders/', ShareholderListView.as_view(), name='shareholder_list'),
    path('shareholders/add/', ShareholderCreateView.as_view(), name='shareholder_create'),
    path('shareholders/<int:pk>/edit/', ShareholderUpdateView.as_view(), name='shareholder_update'),
    path('shareholders/<int:pk>/delete/', ShareholderDeleteView.as_view(), name='shareholder_delete'),

    # Equity Transaction
    path('equity-transactions/', EquityTransactionListView.as_view(), name='equity_transaction_list'),
    path('equity-transactions/add/', EquityTransactionCreateView.as_view(), name='equity_transaction_create'),
    path('equity-transactions/<int:pk>/edit/', EquityTransactionUpdateView.as_view(), name='equity_transaction_update'),
    path('equity-transactions/<int:pk>/delete/', EquityTransactionDeleteView.as_view(), name='equity_transaction_delete'),

    # Shareholder Register
    path('shareholder-registers/', ShareholderRegisterListView.as_view(), name='shareholder_register_list'),
    path('shareholder-registers/add/', ShareholderRegisterCreateView.as_view(), name='shareholder_register_create'),
    path('shareholder-registers/<int:pk>/edit/', ShareholderRegisterUpdateView.as_view(), name='shareholder_register_update'),
    path('shareholder-registers/<int:pk>/delete/', ShareholderRegisterDeleteView.as_view(), name='shareholder_register_delete'),

    # Company Filing (Company Law 22-1)
    path('company-filings/', CompanyFilingListView.as_view(), name='company_filing_list'),
    path('company-filings/add/', CompanyFilingCreateView.as_view(), name='company_filing_create'),
    path('company-filings/<int:pk>/edit/', CompanyFilingUpdateView.as_view(), name='company_filing_edit'),
    path('company-filings/<int:pk>/delete/', CompanyFilingDeleteView.as_view(), name='company_filing_delete'),

    # Filing History
    path('filing-history/<int:pk>/edit/', FilingHistoryUpdateView.as_view(), name='filing_history_edit'),
    path('filing-history/<int:pk>/delete/', FilingHistoryDeleteView.as_view(), name='filing_history_delete'),

    # VAT Entity Change
    path('vat-entity-change/', VATEntityChangeListView.as_view(), name='vat_entity_change_list'),
    path('vat-entity-change/add/', VATEntityChangeCreateView.as_view(), name='vat_entity_change_create'),
    path('vat-entity-change/<int:pk>/edit/', VATEntityChangeUpdateView.as_view(), name='vat_entity_change_update'),
    path('vat-entity-change/<int:pk>/delete/', VATEntityChangeDeleteView.as_view(), name='vat_entity_change_delete'),
]
