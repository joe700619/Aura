"""客戶端路由（mounted at /portal/cases/）"""
from django.urls import path

from .views import (
    PortalCaseListView, PortalCaseCreateView, PortalCaseDetailView, PortalCaseReplyView,
    PortalChecklistTemplateView,
)

app_name = 'case_portal'

urlpatterns = [
    path('', PortalCaseListView.as_view(), name='list'),
    path('new/', PortalCaseCreateView.as_view(), name='create'),
    path('checklist/', PortalChecklistTemplateView.as_view(), name='checklist'),
    path('<int:pk>/', PortalCaseDetailView.as_view(), name='detail'),
    path('<int:pk>/reply/', PortalCaseReplyView.as_view(), name='reply'),
]
