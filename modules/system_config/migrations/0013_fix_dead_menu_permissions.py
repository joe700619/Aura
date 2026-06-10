"""
修正選單指向「已刪除 model」的 required_permission。

- 營所稅申報（bookkeeping:income_tax_list）原指向 bookkeeping.view_incometax，
  但 IncomeTax model 已在 bookkeeping 0015（2026-02-28）刪除，該 permission
  不存在，非 superuser 一律看不到此選單 → 改指向 view_incometaxsetting。
- 記帳進度表（bookkeeping:progress_list）原指向 bookkeeping.view_progress，
  Progress model 已在 bookkeeping 0021（2026-03-06）刪除 → 改指向
  view_bookkeepingperiod。
"""
from django.db import migrations

FIXES = {
    'bookkeeping:income_tax_list': (
        'bookkeeping.view_incometax', 'bookkeeping.view_incometaxsetting'),
    'bookkeeping:progress_list': (
        'bookkeeping.view_progress', 'bookkeeping.view_bookkeepingperiod'),
}


def fix_permissions(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    for url_name, (_old, new) in FIXES.items():
        MenuItem.objects.filter(url_name=url_name).update(required_permission=new)


def revert_permissions(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    for url_name, (old, _new) in FIXES.items():
        MenuItem.objects.filter(url_name=url_name).update(required_permission=old)


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0012_restore_business_registration_menu'),
    ]

    operations = [
        migrations.RunPython(fix_permissions, revert_permissions),
    ]
