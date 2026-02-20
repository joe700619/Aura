from django.urls import path
from . import views

urlpatterns = [
    path('templates/', views.GetEmailTemplatesView.as_view(), name='get_templates'),
    path('send/<str:app_label>/<str:model_name>/<int:object_id>/', views.SendEmailView.as_view(), name='send_email'),
    path('send/bulk/<str:app_label>/<str:model_name>/', views.SendBulkEmailView.as_view(), name='send_bulk_email'),
    path('line/templates/', views.GetLineTemplatesView.as_view(), name='get_line_templates'),
    path('line/send/<str:app_label>/<str:model_name>/<int:object_id>/', views.SendLineView.as_view(), name='send_line'),
    path('line/send/bulk/<str:app_label>/<str:model_name>/', views.SendBulkLineView.as_view(), name='send_bulk_line'),
]
