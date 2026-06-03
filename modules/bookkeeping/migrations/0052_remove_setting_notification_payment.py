from django.db import migrations


class Migration(migrations.Migration):
    """移除 TaxFilingSetting / IncomeTaxSetting 上已停用的 notification_method、
    payment_method 欄位。通知方式與預設繳稅方式現已統一存放於 BookkeepingClient
    (見 migration 0037)，這兩個設定表上的同名欄位自此為死欄位，全面移除。"""

    dependencies = [
        ('bookkeeping', '0051_alter_bookkeepingclient_acceptance_status_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taxfilingsetting',
            name='notification_method',
        ),
        migrations.RemoveField(
            model_name='taxfilingsetting',
            name='payment_method',
        ),
        migrations.RemoveField(
            model_name='historicaltaxfilingsetting',
            name='notification_method',
        ),
        migrations.RemoveField(
            model_name='historicaltaxfilingsetting',
            name='payment_method',
        ),
        migrations.RemoveField(
            model_name='incometaxsetting',
            name='notification_method',
        ),
        migrations.RemoveField(
            model_name='incometaxsetting',
            name='payment_method',
        ),
        migrations.RemoveField(
            model_name='historicalincometaxsetting',
            name='notification_method',
        ),
        migrations.RemoveField(
            model_name='historicalincometaxsetting',
            name='payment_method',
        ),
    ]
