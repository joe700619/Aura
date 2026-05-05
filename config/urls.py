from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/',  auth_views.LoginView.as_view(),  name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('__reload__/', include('django_browser_reload.urls')),
    path('', views.dashboard, name='dashboard'),
    path('core/', include('core.urls')),
    path('bookkeeping/', include('modules.bookkeeping.urls')),
    path('basic-data/', include('modules.basic_data.urls')),
    path('administrative/', include('modules.administrative.urls')),
    path('hr/', include('modules.hr.urls')),
    path('registration/', include('modules.registration.urls')),
    path('payment/', include('modules.payment.urls')),
    path('accounting/', include('modules.internal_accounting.urls')),
    path('portal/', include('modules.client_portal.urls')),
    path('cases/', include('modules.case_management.urls')),
    path('portal/cases/', include('modules.case_management.urls_portal')),
    path('knowledge/', include('modules.knowledge_base.urls')),
    path('site/', include('modules.public_site.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
