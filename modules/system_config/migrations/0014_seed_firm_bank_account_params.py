from django.db import migrations


FIRM_BANK_PARAMS = [
    ('FIRM_BANK_NAME', '事務所收款銀行（含分行），顯示於客戶端匯款頁'),
    ('FIRM_BANK_ACCOUNT_NAME', '事務所收款帳戶戶名，顯示於客戶端匯款頁'),
    ('FIRM_BANK_ACCOUNT_NO', '事務所收款帳號，顯示於客戶端匯款頁'),
]


def seed_params(apps, schema_editor):
    SystemParameter = apps.get_model('system_config', 'SystemParameter')
    for key, description in FIRM_BANK_PARAMS:
        SystemParameter.objects.get_or_create(
            key=key,
            defaults={'value': '', 'description': description, 'group': 'other'},
        )


def unseed_params(apps, schema_editor):
    SystemParameter = apps.get_model('system_config', 'SystemParameter')
    SystemParameter.objects.filter(key__in=[k for k, _ in FIRM_BANK_PARAMS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0013_fix_dead_menu_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_params, unseed_params),
    ]
