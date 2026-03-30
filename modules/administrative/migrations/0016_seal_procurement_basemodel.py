from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('administrative', '0015_irs_audit_notice_attachment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- SealProcurement: add BaseModel fields ---
        migrations.AddField(
            model_name='sealprocurement',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='是否刪除'),
        ),
        # created_at & updated_at already exist on SealProcurement; no need to add

        # --- SealProcurementItem: add BaseModel fields ---
        migrations.AddField(
            model_name='sealprocurementitem',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='是否刪除'),
        ),
        migrations.AddField(
            model_name='sealprocurementitem',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='建立時間'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sealprocurementitem',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新時間'),
        ),

        # --- HistoricalSealProcurement ---
        migrations.CreateModel(
            name='HistoricalSealProcurement',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否刪除')),
                ('created_at', models.DateTimeField(blank=True, editable=False, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(blank=True, editable=False, verbose_name='更新時間')),
                ('unified_business_no', models.CharField(blank=True, default='', max_length=20, verbose_name='統一編號')),
                ('company_name', models.CharField(blank=True, default='', max_length=100, verbose_name='公司名稱')),
                ('line_id', models.CharField(blank=True, default='', max_length=50, verbose_name='Line ID')),
                ('room_id', models.CharField(blank=True, default='', max_length=50, verbose_name='Room ID')),
                ('main_contact', models.CharField(blank=True, default='', max_length=50, verbose_name='主要聯絡人')),
                ('mobile', models.CharField(blank=True, default='', max_length=20, verbose_name='手機')),
                ('phone', models.CharField(blank=True, default='', max_length=30, verbose_name='電話')),
                ('address', models.CharField(blank=True, default='', max_length=200, verbose_name='通訊地址')),
                ('transfer_to_advance', models.BooleanField(default=False, verbose_name='轉為代墊款')),
                ('transfer_to_inventory', models.BooleanField(default=False, verbose_name='轉為庫存')),
                ('seal_cost_subtotal', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='印章費用小計')),
                ('is_paid', models.BooleanField(default=False, verbose_name='是否已付款')),
                ('note', models.TextField(blank=True, default='', verbose_name='備註')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical 印章採購單',
                'verbose_name_plural': 'historical 印章採購單',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),

        # --- HistoricalSealProcurementItem ---
        migrations.CreateModel(
            name='HistoricalSealProcurementItem',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否刪除')),
                ('created_at', models.DateTimeField(blank=True, editable=False, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(blank=True, editable=False, verbose_name='更新時間')),
                ('is_absorbed_by_customer', models.BooleanField(default=False, verbose_name='客戶吸收')),
                ('movement_type', models.CharField(choices=[('purchase', '採購'), ('customer_provided', '客戶提供'), ('return_to_customer', '歸還客戶'), ('lend_out', '借出'), ('borrow_in', '借入'), ('surplus', '盤盈'), ('deficit', '盤虧')], default='purchase', max_length=30, verbose_name='異動類別')),
                ('seal_type', models.CharField(choices=[('large_self', '大章(自留)'), ('small_self', '小章(自留)'), ('large_reg', '大章(登記)'), ('small_reg', '小章(登記)'), ('invoice', '發票章')], default='large_self', max_length=20, verbose_name='印章種類')),
                ('quantity', models.IntegerField(default=1, verbose_name='數量')),
                ('name_or_address', models.CharField(blank=True, default='', max_length=200, verbose_name='名稱/地址')),
                ('unit_price', models.DecimalField(decimal_places=0, default=150, max_digits=10, verbose_name='單價')),
                ('subtotal', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='合計')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('procurement', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='administrative.sealprocurement', verbose_name='採購單')),
            ],
            options={
                'verbose_name': 'historical 印章請購明細',
                'verbose_name_plural': 'historical 印章請購明細',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
