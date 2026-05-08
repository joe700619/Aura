from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/',  auth_views.LoginView.as_view(),  name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('__reload__/', include('django_browser_reload.urls')),
    path('dashboard/', views.dashboard, name='dashboard'),
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
    path('', include('modules.public_site.urls')),

    # Wagtail CMS
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('', include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # django-debug-toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        from debug_toolbar.toolbar import debug_toolbar_urls
        urlpatterns += debug_toolbar_urls()
