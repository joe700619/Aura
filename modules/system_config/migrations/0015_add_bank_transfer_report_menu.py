"""
新增「銀行匯款回報」選單項目（內部會計 → 收款管理 之後）
"""
from django.db import migrations


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='內部會計', parent__isnull=True).first()
    if not parent:
        return  # 防呆：父層不存在就跳過
    MenuItem.objects.update_or_create(
        title='銀行匯款回報',
        parent=parent,
        defaults={
            'url_name': 'internal_accounting:bank_transfer_report_list',
            'icon_svg': '',
            'order': 45,
            'is_active': True,
            'required_permission': '',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='內部會計', parent__isnull=True).first()
    if parent:
        MenuItem.objects.filter(title='銀行匯款回報', parent=parent).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0014_seed_firm_bank_account_params'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
