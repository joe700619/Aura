from django.urls import path, include
from . import views

urlpatterns = [
    path('export/fields/<str:app_label>/<str:model_name>/', views.ExportFieldsView.as_view(), name='export_fields'),
    path('export/<str:app_label>/<str:model_name>/', views.ExportDataView.as_view(), name='export_data'),
    
    # Document Generation
    path('documents/templates/<str:app_label>/<str:model_name>/', views.GetTemplatesView.as_view(), name='get_templates'),
    path('documents/variables/<str:app_label>/<str:model_name>/', views.get_model_variables, name='get_model_variables'),
    path('documents/generate/<int:template_id>/<str:app_label>/<str:model_name>/<int:object_id>/', views.GenerateDocumentView.as_view(), name='generate_document'),
    # Notifications
    path('notifications/', include('core.notifications.urls')),
    
    # System Config
    path('system/', include('modules.system_config.urls')),
]
