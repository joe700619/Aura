from django.apps import AppConfig

class BookkeepingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.bookkeeping'
    verbose_name = '記帳業務'

    def ready(self):
        import modules.bookkeeping.models.signals
