"""初始化勞報繳費提醒所需資料（ScheduledJob、Email/LINE 範本）。

直接呼叫既有的 init_remuneration_reminder command：
- get_or_create / update_or_create，重跑安全，不會覆寫 admin 已修改的範本內容
- 包成 migration 是為了讓 Railway 部署時自動執行，不需手動進容器
"""
from django.core.management import call_command
from django.db import migrations


def init_reminder_data(apps, schema_editor):
    call_command('init_remuneration_reminder')


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0054_remove_historicalserviceremuneration_payment_status_and_more'),
        ('core', '0008_scheduledjob'),
    ]

    operations = [
        migrations.RunPython(init_reminder_data, migrations.RunPython.noop),
    ]
