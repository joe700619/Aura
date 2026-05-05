from django.apps import AppConfig


class CaseManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.case_management'
    verbose_name = '案件管理'

    def ready(self):
        from . import signals  # noqa: F401
