from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administrative', '0016_seal_procurement_basemodel'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE administrative_sealprocurement
                ADD COLUMN IF NOT EXISTS is_advance_transferred boolean NOT NULL DEFAULT false;

                ALTER TABLE administrative_historicalsealprocurement
                ADD COLUMN IF NOT EXISTS is_advance_transferred boolean NOT NULL DEFAULT false;
            """,
            reverse_sql="""
                ALTER TABLE administrative_sealprocurement
                DROP COLUMN IF EXISTS is_advance_transferred;

                ALTER TABLE administrative_historicalsealprocurement
                DROP COLUMN IF EXISTS is_advance_transferred;
            """,
            state_operations=[
                migrations.AddField(
                    model_name='sealprocurement',
                    name='is_advance_transferred',
                    field=models.BooleanField(default=False, verbose_name='已拋轉代墊款'),
                ),
                migrations.AddField(
                    model_name='historicalsealprocurement',
                    name='is_advance_transferred',
                    field=models.BooleanField(default=False, verbose_name='已拋轉代墊款'),
                ),
            ],
        ),
    ]
