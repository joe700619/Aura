"""初始化記帳委任書 v1 範本與邀請 Email 範本。

呼叫 init_engagement_letter command（get_or_create，重跑安全），
讓部署自動建立預設骨架範本，所內之後在後台改條款＝新增版本列。
"""
from django.core.management import call_command
from django.db import migrations


def init_data(apps, schema_editor):
    call_command('init_engagement_letter')


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0063_engagementlettertemplate_historicalengagementletter_and_more'),
    ]

    operations = [
        migrations.RunPython(init_data, migrations.RunPython.noop),
    ]
