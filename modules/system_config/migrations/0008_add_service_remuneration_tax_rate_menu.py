from django.db import migrations


def add_menu(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title__in=['記帳', '記帳業務']).first()
    if not parent:
        parent = MenuItem.objects.filter(pk=5).first()
    MenuItem.objects.update_or_create(
        url_name='bookkeeping:service_remuneration_tax_rate_list',
        defaults={
            'parent': parent,
            'title': '勞務報酬稅率設定',
            'order': 96,
            'is_active': True,
            'required_permission': 'bookkeeping.view_serviceremunerationtaxrate',
        },
    )


def remove_menu(apps, _schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(url_name='bookkeeping:service_remuneration_tax_rate_list').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0007_add_business_registration_menu'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
