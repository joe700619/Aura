from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'client_portal'

urlpatterns = [
    path('login/', views.PortalLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='client_portal:login'), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('vat/', views.DocumentCenterView.as_view(), name='vat_documents'),
]
