from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'client_portal'

urlpatterns = [
    path('login/', views.PortalLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='client_portal:login'), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('vat/', views.DocumentCenterView.as_view(), name='vat_documents'),
    path('shareholders/', views.ShareholderManagementView.as_view(), name='shareholders'),
    path('financial-analysis/', views.FinancialAnalysisView.as_view(), name='financial_analysis'),
    path('income-declaration/', views.IncomeDeclarationView.as_view(), name='income_declaration'),
    path('dividend-declaration/', views.DividendDeclarationView.as_view(), name='dividend_declaration'),
    path('service-remuneration/', views.ServiceRemunerationView.as_view(), name='service_remuneration'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
]
