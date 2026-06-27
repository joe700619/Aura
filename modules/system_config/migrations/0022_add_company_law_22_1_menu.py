"""新增「公司法22-1申報」側選單。

掛在「記帳」父選單下，入口指向 /bookkeeping/company-law-22-1/。
"""
from django.db import migrations


FILING_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M9 2h6l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z"/>'
    '<path d="M14 2v5h5M9 13l2 2 4-4"/></svg>'
)


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if not parent:
        return
    MenuItem.objects.update_or_create(
        title='公司法22-1申報',
        parent=parent,
        defaults={
            'url_name': 'bookkeeping:company_law_22_1_list',
            'icon_svg': FILING_ICON,
            'order': 7,
            'is_active': True,
            'required_permission': '',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent:
        MenuItem.objects.filter(title='公司法22-1申報', parent=parent).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0021_add_engagement_letter_menu'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
