from django.apps import AppConfig

class BookkeepingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.bookkeeping'

    def ready(self):
        import modules.bookkeeping.models.signals
