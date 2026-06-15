"""
移除「登記」下的重複選單。

成因：0009 種了舊名稱（股東及董事名單 / 股權交易紀錄），0010 由 snapshot 以
新名稱（股東及董監事名單 / 股權交易）update_or_create，但 update_or_create 以
(title, parent) 為鍵，不會刪舊列 → 全新環境（如正式站）兩個 view 各會留下兩筆。

本 migration 對「登記」下這兩個 url_name 去重，只保留正規標題那一筆，刪掉其餘。
在已乾淨的環境（如本機 dev）為 no-op。
"""
from django.db import migrations


CANONICAL = {
    'registration:shareholder_list': '股東及董監事名單',
    'registration:equity_transaction_list': '股權交易',
    'registration:shareholder_register_list': '股東名簿查詢',
}


def dedup(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='登記', parent__isnull=True).first()
    if not parent:
        return  # 防呆：父層不存在就跳過

    for url_name, keep_title in CANONICAL.items():
        items = list(
            MenuItem.objects.filter(parent=parent, url_name=url_name).order_by('id')
        )
        if len(items) <= 1:
            continue  # 沒有重複，跳過

        # 優先保留正規標題那筆，否則保留最早建立的
        keeper = next((i for i in items if i.title == keep_title), items[0])
        if keeper.title != keep_title:
            keeper.title = keep_title
            keeper.save()
        for item in items:
            if item.id != keeper.id:
                item.delete()


def noop(apps, schema_editor):
    """rollback 是 no-op（不還原已刪的重複列）"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('system_config', '0016_add_service_remuneration_menu'),
    ]
    operations = [
        migrations.RunPython(dedup, noop),
    ]
