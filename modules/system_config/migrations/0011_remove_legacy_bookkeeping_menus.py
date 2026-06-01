"""
移除舊開發遺留的選單：商工登記、勞務報酬稅率設定

成因：
- 0007 以 url_name 為鍵、0009 以 (title, parent=記帳) 為鍵分別建立同一個
  「商工登記」，兩者 parent 不同 → DB 出現重複列（navbar 看到兩張）。
- 「勞務報酬稅率設定」同屬舊 bookkeeping 開發功能。

本 migration 只清除 system_config_menuitem 內這兩個 url_name 的選單列
（含重複列），不動底層 model / view / url。
"""
from django.db import migrations


LEGACY_URL_NAMES = [
    'bookkeeping:business_registration_list',
    'bookkeeping:service_remuneration_tax_rate_list',
]


def remove_menus(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(url_name__in=LEGACY_URL_NAMES).delete()


def restore_menus(apps, _schema_editor):
    """rollback：在『記帳』底下補回這兩個選單（best-effort）"""
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent is None:
        return
    MenuItem.objects.update_or_create(
        url_name='bookkeeping:business_registration_list',
        defaults={
            'parent': parent,
            'title': '商工登記',
            'order': 37,
            'is_active': True,
            'required_permission': 'bookkeeping.view_businessregistration',
        },
    )
    MenuItem.objects.update_or_create(
        url_name='bookkeeping:service_remuneration_tax_rate_list',
        defaults={
            'parent': parent,
            'title': '勞務報酬稅率設定',
            'order': 44,
            'is_active': True,
            'required_permission': 'bookkeeping.view_serviceremunerationtaxrate',
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0010_reorder_and_add_knowledge_base_20260508'),
    ]

    operations = [
        migrations.RunPython(remove_menus, restore_menus),
    ]
