"""初始化記帳 onboarding SLA 催促所需資料（Group、ScheduledJob、Email 範本）。

呼叫既有的 init_onboarding_sla command：
- get_or_create / update_or_create，重跑安全，不覆寫 admin 已改的範本
- 包成 migration 讓 Railway 部署自動執行，不需手動進容器
"""
from django.core.management import call_command
from django.db import migrations


def init_sla_data(apps, schema_editor):
    call_command('init_onboarding_sla')


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0061_bookkeepingclient_assigned_at_and_more'),
        ('core', '0008_scheduledjob'),
        ('auth', '__first__'),
    ]

    operations = [
        migrations.RunPython(init_sla_data, migrations.RunPython.noop),
    ]
