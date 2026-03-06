import django
from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest
from django.contrib.auth import get_user_model

django.setup()
admin.autodiscover()

User = get_user_model()
su = User.objects.filter(is_superuser=True).first()
if not su:
    print("NO SUPERUSER FOUND")
else:
    request = HttpRequest()
    request.user = su
    
    apps = admin.site.get_app_list(request)
    print(f"Total apps visible to superuser: {len(apps)}")
    for app in apps:
        print(f"\n[{app['app_label']}] - {app['name']}")
        for model in app['models']:
            print(f"  - {model['name']}")
