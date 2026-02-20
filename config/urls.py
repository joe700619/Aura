from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('__reload__/', include('django_browser_reload.urls')),
    path('', views.dashboard, name='dashboard'),
    path('core/', include('core.urls')),
    path('bookkeeping/', include('modules.bookkeeping.urls')),
    path('basic-data/', include('modules.basic_data.urls')),
    path('hr/', include('modules.hr.urls')),
    path('registration/', include('modules.registration.urls')),
    path('payment/', include('modules.payment.urls')),
]
