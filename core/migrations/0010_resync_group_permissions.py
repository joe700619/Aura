"""
重新同步 Groups 的 model permissions（補 0007 之後新增 model 的權限）。

背景：0007_add_permission_groups（2026-04-15）把「當時存在」的 permissions
派給各 Group，但之後新增的 model（如 4/25 的 BusinessRegistration、
ServiceRemunerationTaxRate）其 permissions 不會自動補進 Group，
導致 A/B/C組 看不到對應選單（選單以 required_permission 判斷可見性）。

做法：只「加」不「減」（union），不會清掉管理者手動加的權限。
"""
from django.db import migrations

BUSINESS_APPS = ['bookkeeping', 'administrative', 'basic_data']
HR_APPS = ['hr', 'basic_data']


def resync_permissions(apps, _schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    business_perms = list(Permission.objects.filter(
        content_type__app_label__in=BUSINESS_APPS))
    hr_perms = list(Permission.objects.filter(
        content_type__app_label__in=HR_APPS))
    all_perms = list(Permission.objects.all())

    for name in ('A組', 'B組', 'C組'):
        grp = Group.objects.filter(name=name).first()
        if grp:
            grp.permissions.add(*business_perms)

    hr_grp = Group.objects.filter(name='人資組').first()
    if hr_grp:
        hr_grp.permissions.add(*hr_perms)

    for name in ('CPA', 'management'):
        grp = Group.objects.filter(name=name).first()
        if grp:
            grp.permissions.add(*all_perms)


def noop(apps, _schema_editor):
    """不還原：移除權限可能影響使用中帳號，rollback 保持現狀。"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_create_pgvector_extension'),
        ('auth', '0012_alter_user_first_name_max_length'),
        # 確保 4/25 新增的 model（商工登記、勞務報酬）permissions 已存在
        ('bookkeeping', '0042_add_service_remuneration'),
    ]

    operations = [
        migrations.RunPython(resync_permissions, noop),
    ]
