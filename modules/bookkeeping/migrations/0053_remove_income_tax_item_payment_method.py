from django.db import migrations


class Migration(migrations.Migration):
    """移除所得稅各申報項目（暫繳/扣繳/股利/結算）的 payment_method 欄位。

    繳稅方式統一改用 BookkeepingClient.payment_method（客戶基本資料的預設值），
    各 per-record 欄位不再使用，全面移除（含 simple_history 歷史表）。
    「無須繳納」狀態改由 filing_status='no_payment_needed' 表示。
    """

    dependencies = [
        ('bookkeeping', '0052_remove_setting_notification_payment'),
    ]

    operations = [
        migrations.RemoveField(model_name='provisionaltax', name='payment_method'),
        migrations.RemoveField(model_name='historicalprovisionaltax', name='payment_method'),
        migrations.RemoveField(model_name='withholdingtax', name='payment_method'),
        migrations.RemoveField(model_name='historicalwithholdingtax', name='payment_method'),
        migrations.RemoveField(model_name='dividendtax', name='payment_method'),
        migrations.RemoveField(model_name='historicaldividendtax', name='payment_method'),
        migrations.RemoveField(model_name='incometaxfiling', name='payment_method'),
        migrations.RemoveField(model_name='historicalincometaxfiling', name='payment_method'),
    ]
