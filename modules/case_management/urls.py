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
    InquiryListView, InquiryDetailView, InquiryUpdateView, InquiryClaimView,
    IntakeWorkbenchView, IntakeReissueLinkView,
    ExternalIntakeView, ExternalIntakeUploadView, ExternalIntakeSubmitView,
    ExternalIntakeDeleteFileView,
    ExternalDeclarationView, ExternalDeclarationSubmitView,
)

app_name = 'case_management'

urlpatterns = [
    path('', InternalCaseListView.as_view(), name='internal_list'),
    path('new/', InternalCaseCreateView.as_view(), name='internal_create'),
    path('api/clients/lookup/', BookkeepingClientLookupView.as_view(), name='api_client_lookup'),
    path('api/users/lookup/', StaffUserLookupView.as_view(), name='api_user_lookup'),
    path('access/<str:token>/', ExternalCaseAccessView.as_view(), name='external_access'),
    path('access/<str:token>/reply/', ExternalCaseReplyView.as_view(), name='external_reply'),

    # 商工登記收料：承辦工作台（掛 Progress 詳情頁）
    path('intake/progress/<int:progress_pk>/', IntakeWorkbenchView.as_view(), name='intake_workbench'),
    path('intake/case/<int:pk>/reissue-link/', IntakeReissueLinkView.as_view(), name='intake_reissue_link'),
    # 商工登記收料：客戶端免登入上傳
    path('intake/access/<str:token>/', ExternalIntakeView.as_view(), name='intake_external'),
    path('intake/access/<str:token>/upload/<int:task_id>/', ExternalIntakeUploadView.as_view(), name='intake_external_upload'),
    path('intake/access/<str:token>/upload/<int:task_id>/delete/<int:doc_id>/', ExternalIntakeDeleteFileView.as_view(), name='intake_external_delete'),
    path('intake/access/<str:token>/declaration/<int:task_id>/', ExternalDeclarationView.as_view(), name='intake_declaration'),
    path('intake/access/<str:token>/declaration/<int:task_id>/submit/', ExternalDeclarationSubmitView.as_view(), name='intake_declaration_submit'),
    path('intake/access/<str:token>/submit/', ExternalIntakeSubmitView.as_view(), name='intake_external_submit'),
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

    # 諮詢預約（潛在客戶）
    path('inquiries/', InquiryListView.as_view(), name='inquiry_list'),
    path('inquiries/<int:pk>/', InquiryDetailView.as_view(), name='inquiry_detail'),
    path('inquiries/<int:pk>/update/', InquiryUpdateView.as_view(), name='inquiry_update'),
    path('inquiries/<int:pk>/claim/', InquiryClaimView.as_view(), name='inquiry_claim'),
]
