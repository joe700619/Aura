"""
撿回「商工登記」選單

背景：
- 0011 為了清掉 navbar 上的重複列，用 url_name 過濾把商工登記「兩列一起刪光」，
  導致選單完全消失（連合法那列也被刪）。
- 本 migration 在「記帳」底下補回『單一』商工登記，欄位照 0009 原樣。

用 (title, parent) 當鍵 + update_or_create → idempotent，重跑不會再生出重複列。
不還原 0011 一併移除的「勞務報酬稅率設定」（那個維持移除）。
"""
from django.db import migrations


def restore_menu(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent is None:
        return  # 防呆：父層不存在就跳過
    MenuItem.objects.update_or_create(
        title='商工登記',
        parent=parent,
        defaults={
            'url_name': 'bookkeeping:business_registration_list',
            'icon_svg': '',
            'order': 37,
            'is_active': True,
            'required_permission': 'bookkeeping.view_businessregistration',
        },
    )


def remove_menu(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(
        title='商工登記', parent__title='記帳',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0011_remove_legacy_bookkeeping_menus'),
    ]

    operations = [
        migrations.RunPython(restore_menu, remove_menu),
    ]
