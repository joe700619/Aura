from django.db import migrations


def add_menu(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title__in=['記帳', '記帳業務']).first()
    if not parent:
        parent = MenuItem.objects.filter(pk=5).first()
    MenuItem.objects.update_or_create(
        url_name='bookkeeping:business_registration_list',
        defaults={
            'parent': parent,
            'title': '商工登記',
            'order': 37,
            'is_active': True,
            'required_permission': 'bookkeeping.view_businessregistration',
        },
    )


def remove_menu(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(url_name='bookkeeping:business_registration_list').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0006_remove_roles_set_permissions'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
