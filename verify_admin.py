import django
from django.conf import settings
from django.contrib import admin
from modules.bookkeeping.models import BookkeepingClient

django.setup()
admin.autodiscover()

is_registered = BookkeepingClient in admin.site._registry
print(f"BookkeepingClient registered in admin: {is_registered}")

if is_registered:
    print(f"Admin class: {admin.site._registry[BookkeepingClient]}")
else:
    print("FAILED TO FIND IN REGISTRY")
