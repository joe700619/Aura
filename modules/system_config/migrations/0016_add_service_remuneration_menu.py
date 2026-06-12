"""
新增「勞務報酬單」選單項目（記帳 → 商工登記 之後）
"""
from django.db import migrations


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if not parent:
        return  # 防呆：父層不存在就跳過
    MenuItem.objects.update_or_create(
        title='勞務報酬單',
        parent=parent,
        defaults={
            'url_name': 'bookkeeping:service_remuneration_list',
            'icon_svg': '',
            'order': 38,
            'is_active': True,
            'required_permission': 'bookkeeping.view_serviceremuneration',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent:
        MenuItem.objects.filter(title='勞務報酬單', parent=parent).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0015_add_bank_transfer_report_menu'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
