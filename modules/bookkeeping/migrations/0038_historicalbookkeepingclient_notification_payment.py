from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0037_bookkeepingclient_notification_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalbookkeepingclient',
            name='notification_method',
            field=models.CharField(
                blank=True, null=True,
                choices=[('line', 'Line'), ('email', 'Email'), ('both', 'Line + Email')],
                max_length=10,
                verbose_name='通知方式',
            ),
        ),
        migrations.AddField(
            model_name='historicalbookkeepingclient',
            name='payment_method',
            field=models.CharField(
                blank=True, null=True,
                choices=[('self_pay', '自行繳納'), ('office_pay', '事務所代繳'), ('auto_debit', '自動扣款')],
                max_length=20,
                verbose_name='預設繳稅方式',
            ),
        ),
    ]
