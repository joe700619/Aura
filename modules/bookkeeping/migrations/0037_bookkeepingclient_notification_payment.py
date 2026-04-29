from django.db import migrations, models


def copy_from_tax_setting(apps, _schema_editor):
    TaxFilingSetting = apps.get_model('bookkeeping', 'TaxFilingSetting')
    for setting in TaxFilingSetting.objects.select_related('client').iterator():
        client = setting.client
        updated = False
        if not client.notification_method and setting.notification_method:
            client.notification_method = setting.notification_method
            updated = True
        if not client.payment_method and setting.payment_method:
            client.payment_method = setting.payment_method
            updated = True
        if updated:
            client.save(update_fields=['notification_method', 'payment_method'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0036_remove_business_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookkeepingclient',
            name='notification_method',
            field=models.CharField(
                blank=True, null=True,
                choices=[('line', 'Line'), ('email', 'Email'), ('both', 'Line + Email')],
                max_length=10,
                verbose_name='通知方式',
            ),
        ),
        migrations.AddField(
            model_name='bookkeepingclient',
            name='payment_method',
            field=models.CharField(
                blank=True, null=True,
                choices=[('self_pay', '自行繳納'), ('office_pay', '事務所代繳'), ('auto_debit', '自動扣款')],
                max_length=20,
                verbose_name='預設繳稅方式',
            ),
        ),
        migrations.RunPython(copy_from_tax_setting, migrations.RunPython.noop),
    ]
