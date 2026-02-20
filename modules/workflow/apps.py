"""
Workflow app configuration
"""
from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.workflow'
    verbose_name = '核准工作流程'
