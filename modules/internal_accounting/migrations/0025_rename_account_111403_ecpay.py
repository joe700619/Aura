from django.db import migrations


def rename_forward(apps, schema_editor):
    """把既有的綠界收款科目 111403 名稱改為「銀行存款_綠界」（科目代號不變）。"""
    Account = apps.get_model('internal_accounting', 'Account')
    Account.objects.filter(code='111403').update(name='銀行存款_綠界')


def rename_backward(apps, schema_editor):
    Account = apps.get_model('internal_accounting', 'Account')
    Account.objects.filter(code='111403').update(name='綠界')


class Migration(migrations.Migration):

    dependencies = [
        ('internal_accounting', '0024_alter_collection_date_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
