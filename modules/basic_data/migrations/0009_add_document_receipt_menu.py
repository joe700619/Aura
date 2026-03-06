import django.db.models.deletion
from django.db import migrations, models

def add_menu_item(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    try:
        parent = MenuItem.objects.get(title='基本資料', parent__isnull=True)
        MenuItem.objects.update_or_create(
            title='收文系統',
            defaults={
                'url_name': 'basic_data:document_receipt_list',
                'parent': parent,
                'order': 50,
                'icon_svg': '<svg fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>',
            }
        )
    except MenuItem.DoesNotExist:
        pass

def remove_menu_item(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(title='收文系統').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('basic_data', '0008_documentreceipt'),
        ('system_config', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_menu_item, remove_menu_item),
    ]
