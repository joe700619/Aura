"""
為既有客戶補建 TaxFilingSetting。

背景：營業稅可見性已改由 service_type 即時判斷（見 BookkeepingClient.VAT_SERVICE_TYPES），
不再以「子檔是否存在」當開關。為維持「每位客戶都有設定檔」的不變式（比照 IncomeTaxSetting），
此 migration 替所有尚未擁有 TaxFilingSetting 的既有客戶補建一筆。

form_type 預設值沿用 signal 邏輯：mixed_direct / mixed_ratio → 403，其餘 → 401。
"""
from django.db import migrations


def backfill_tax_filing_setting(apps, schema_editor):
    BookkeepingClient = apps.get_model('bookkeeping', 'BookkeepingClient')
    TaxFilingSetting = apps.get_model('bookkeeping', 'TaxFilingSetting')

    mixed = ('mixed_direct', 'mixed_ratio')
    existing_client_ids = set(
        TaxFilingSetting.objects.values_list('client_id', flat=True)
    )

    to_create = []
    for client in BookkeepingClient.objects.exclude(id__in=existing_client_ids).iterator():
        form_type = '403' if client.service_type in mixed else '401'
        to_create.append(TaxFilingSetting(client_id=client.id, form_type=form_type))

    TaxFilingSetting.objects.bulk_create(to_create, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0058_remove_businessregistrationdocument_file_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_tax_filing_setting, migrations.RunPython.noop),
    ]
