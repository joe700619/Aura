from django.apps import AppConfig


class HrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.hr'
    verbose_name = '人力資源'

    def ready(self):
        import modules.hr.signals  # noqa: F401
