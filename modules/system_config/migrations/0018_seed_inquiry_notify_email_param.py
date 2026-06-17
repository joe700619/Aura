from django.db import migrations


KEY = 'INQUIRY_NOTIFY_EMAIL'
DESCRIPTION = '官網諮詢 / 快速登記表單送出時，通知事務所的收件信箱（多個用逗號分隔；留空不寄）'


def seed_param(apps, schema_editor):
    SystemParameter = apps.get_model('system_config', 'SystemParameter')
    SystemParameter.objects.get_or_create(
        key=KEY,
        defaults={'value': '', 'description': DESCRIPTION, 'group': 'email'},
    )


def unseed_param(apps, schema_editor):
    SystemParameter = apps.get_model('system_config', 'SystemParameter')
    SystemParameter.objects.filter(key=KEY).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0017_dedup_registration_shareholder_menus'),
    ]

    operations = [
        migrations.RunPython(seed_param, unseed_param),
    ]
