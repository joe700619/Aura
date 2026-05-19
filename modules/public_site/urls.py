from django.urls import path

from . import views
from .views_inquiry import submit_inquiry

app_name = "public_site"

urlpatterns = [
    path("inquiry/submit/", submit_inquiry, name="inquiry_submit"),
    path("", views.LandingView.as_view(), name="landing"),
    path("family-office/", views.FamilyOfficeView.as_view(), name="family_office"),
    path("services/bookkeeping/", views.BookkeepingView.as_view(), name="bookkeeping"),
    path("services/attestation/", views.AttestationView.as_view(), name="attestation"),
    path("services/registration/", views.RegistrationView.as_view(), name="registration"),
    path("services/advisory/", views.AdvisoryView.as_view(), name="advisory"),
    path("tools/labor-insurance/", views.LaborInsuranceView.as_view(), name="labor_insurance"),
    path("tools/payment-receipt/", views.PaymentReceiptView.as_view(), name="payment_receipt"),
    path("tools/startup-analysis/", views.StartupAnalysisView.as_view(), name="startup_analysis"),
    path("tools/withholding-tax/", views.WithholdingTaxView.as_view(), name="withholding_tax"),
    path("tools/process-flow/", views.ProcessFlowView.as_view(), name="process_flow"),
]
