from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0056_alter_historicalserviceremuneration_premium_payment_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxfilingperiod',
            name='sales_return',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=15, verbose_name='銷項退回及折讓-銷售額'),
        ),
        migrations.AddField(
            model_name='taxfilingperiod',
            name='sales_return_tax',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=15, verbose_name='銷項退回及折讓-稅額'),
        ),
        migrations.AddField(
            model_name='historicaltaxfilingperiod',
            name='sales_return',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=15, verbose_name='銷項退回及折讓-銷售額'),
        ),
        migrations.AddField(
            model_name='historicaltaxfilingperiod',
            name='sales_return_tax',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=15, verbose_name='銷項退回及折讓-稅額'),
        ),
    ]
