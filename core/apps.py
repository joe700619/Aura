from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.auth.admin
        # Ensure main admin is loaded if not auto-discovered
        try:
            import core.admin
            import core.notifications.admin
        except ImportError:
            pass
