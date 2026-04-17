from django.db import migrations

PERIOD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>'


def add_period_menu_item(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')

    # Find the internal accounting parent (the item that contains voucher_list as a child)
    voucher_item = MenuItem.objects.filter(url_name='internal_accounting:voucher_list').first()
    if not voucher_item or not voucher_item.parent_id:
        return

    parent_id = voucher_item.parent_id

    # Avoid duplicates
    if MenuItem.objects.filter(url_name='internal_accounting:period_list').exists():
        return

    # Insert after fixed_asset_list (order=100) → use 102
    MenuItem.objects.create(
        parent_id=parent_id,
        title='會計期間管理',
        url_name='internal_accounting:period_list',
        icon_svg=PERIOD_SVG,
        order=102,
        is_active=True,
    )


def remove_period_menu_item(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(url_name='internal_accounting:period_list').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0002_systemparameter'),
    ]

    operations = [
        migrations.RunPython(add_period_menu_item, remove_period_menu_item),
    ]
