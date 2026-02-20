from django.apps import AppConfig

class BasicDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.basic_data'
    verbose_name = '基本資料'
