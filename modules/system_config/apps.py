from django.apps import AppConfig


class SystemConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.system_config'

    def ready(self):
        import modules.system_config.signals  # noqa: F401
