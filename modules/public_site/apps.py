from django.apps import AppConfig


class PublicSiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.public_site"
    label = "public_site"
    verbose_name = "對外網站"
