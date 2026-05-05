from django.urls import path
from . import views

app_name = 'knowledge_base'

urlpatterns = [
    path('', views.KnowledgeBaseView.as_view(), name='index'),
    path('search/', views.KnowledgeSearchView.as_view(), name='search'),
    path('review/', views.KnowledgeReviewListView.as_view(), name='review_list'),
    path('review/<int:pk>/action/', views.KnowledgeReviewActionView.as_view(), name='review_action'),
    path('extract/case/<int:case_pk>/', views.KnowledgeExtractView.as_view(), name='extract_from_case'),
    path('suggest/case/<int:case_pk>/', views.KnowledgeSuggestView.as_view(), name='suggest_for_case'),
    path('apply-checklist/case/<int:case_pk>/', views.KnowledgeApplyChecklistView.as_view(), name='apply_checklist_to_case'),
]
