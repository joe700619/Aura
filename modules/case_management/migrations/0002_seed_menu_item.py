"""加入內部 sidebar 的「案件管理」選單項目"""
from django.db import migrations


SVG = ('<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" '
       'stroke-width="1.5" stroke="currentColor" class="w-6 h-6">'
       '<path stroke-linecap="round" stroke-linejoin="round" '
       'd="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 '
       '012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>')


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.get_or_create(
        url_name='case_management:internal_list',
        defaults={
            'title': '案件管理',
            'icon_svg': SVG,
            'order': 50,
            'is_active': True,
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(url_name='case_management:internal_list').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('case_management', '0001_initial'),
        ('system_config', '0008_add_service_remuneration_tax_rate_menu'),
    ]
    operations = [migrations.RunPython(add_menu, remove_menu)]
