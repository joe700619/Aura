from django.db import migrations


def rename_forward(apps, schema_editor):
    """把既有的國泰世華收款科目 111401 名稱改為「銀行存款_國泰世華」（科目代號不變）。"""
    Account = apps.get_model('internal_accounting', 'Account')
    Account.objects.filter(code='111401').update(name='銀行存款_國泰世華')


def rename_backward(apps, schema_editor):
    Account = apps.get_model('internal_accounting', 'Account')
    Account.objects.filter(code='111401').update(name='國泰世華')


class Migration(migrations.Migration):

    dependencies = [
        ('internal_accounting', '0025_rename_account_111403_ecpay'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
