from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'client_portal'

urlpatterns = [
    path('login/', views.PortalLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='client_portal:login'), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('billing/', views.BillingView.as_view(), name='billing'),
    path('billing/<int:pk>/pay/', views.GeneratePaymentLinkView.as_view(), name='billing_pay'),
    path('billing/<int:pk>/pdf/', views.DownloadBillPdfView.as_view(), name='billing_pdf'),
    path('vat/', views.DocumentCenterView.as_view(), name='vat_documents'),
    path('shareholders/', views.ShareholderManagementView.as_view(), name='shareholders'),
    path('financial-analysis/', views.FinancialAnalysisView.as_view(), name='financial_analysis'),
    path('income-declaration/', views.IncomeDeclarationView.as_view(), name='income_declaration'),
    path('dividend-declaration/', views.DividendDeclarationView.as_view(), name='dividend_declaration'),
    path('service-remuneration/', views.ServiceRemunerationView.as_view(), name='service_remuneration'),
    path('service-remuneration/save/', views.ServiceRemunerationSaveView.as_view(), name='service_remuneration_save'),
    path('service-remuneration/<int:pk>/delete/', views.ServiceRemunerationDeleteView.as_view(), name='service_remuneration_delete'),
    path('service-remuneration/<int:pk>/upload-slip/', views.ServiceRemunerationUploadSlipView.as_view(), name='service_remuneration_upload_slip'),
    path('service-remuneration/<int:pk>/download-slip/', views.ServiceRemunerationDownloadSlipView.as_view(), name='service_remuneration_download_slip'),
    path('service-remuneration/<int:pk>/tax152-pdf/', views.ServiceRemunerationTax152PdfView.as_view(), name='service_remuneration_tax152_pdf'),
    path('service-remuneration/<int:pk>/pdf/', views.ServiceRemunerationPdfView.as_view(), name='service_remuneration_pdf'),
    # 公開確認頁（不需登入）
    path('service-remuneration/confirm/<uuid:token>/', views.ServiceRemunerationConfirmView.as_view(), name='service_remuneration_confirm'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('tax152/', views.Tax152View.as_view(), name='tax152'),

    # 忘記密碼系列
    path('password-reset/', views.ClientPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.ClientPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.ClientPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.ClientPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
