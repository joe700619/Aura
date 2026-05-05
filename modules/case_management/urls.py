"""內部 + 外部 magic link 路由（mounted at /cases/）"""
from django.urls import path

from .views import (
    InternalCaseListView, InternalCaseDetailView, InternalCaseCreateView,
    InternalCaseReplyView, InternalCaseTaskAddView, InternalCaseTaskToggleView,
    InternalCaseTaskHideView, InternalCaseTaskReorderView,
    InternalCaseAttachmentUploadView, InternalCaseStatusUpdateView,
    InternalCaseIssueMagicLinkView,
    ExternalCaseAccessView, ExternalCaseReplyView,
    BookkeepingClientLookupView, StaffUserLookupView,
    ClientCaseAnalyticsView,
)

app_name = 'case_management'

urlpatterns = [
    path('', InternalCaseListView.as_view(), name='internal_list'),
    path('new/', InternalCaseCreateView.as_view(), name='internal_create'),
    path('api/clients/lookup/', BookkeepingClientLookupView.as_view(), name='api_client_lookup'),
    path('api/users/lookup/', StaffUserLookupView.as_view(), name='api_user_lookup'),
    path('access/<str:token>/', ExternalCaseAccessView.as_view(), name='external_access'),
    path('access/<str:token>/reply/', ExternalCaseReplyView.as_view(), name='external_reply'),
    path('<int:pk>/', InternalCaseDetailView.as_view(), name='internal_detail'),
    path('<int:pk>/reply/', InternalCaseReplyView.as_view(), name='internal_reply'),
    path('<int:pk>/status/', InternalCaseStatusUpdateView.as_view(), name='internal_status'),
    path('<int:pk>/task/add/', InternalCaseTaskAddView.as_view(), name='internal_task_add'),
    path('<int:pk>/task/<int:task_id>/toggle/', InternalCaseTaskToggleView.as_view(), name='internal_task_toggle'),
    path('<int:pk>/task/<int:task_id>/hide/', InternalCaseTaskHideView.as_view(), name='internal_task_hide'),
    path('<int:pk>/task/reorder/', InternalCaseTaskReorderView.as_view(), name='internal_task_reorder'),
    path('<int:pk>/attachment/', InternalCaseAttachmentUploadView.as_view(), name='internal_attachment'),
    path('<int:pk>/magic-link/', InternalCaseIssueMagicLinkView.as_view(), name='internal_magic_link'),
    path('analytics/clients/', ClientCaseAnalyticsView.as_view(), name='client_analytics'),
]
