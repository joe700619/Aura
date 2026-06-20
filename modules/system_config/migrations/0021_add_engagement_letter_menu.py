"""新增「記帳委任書」側選單（斷點：工商轉記帳的委任）。

掛在「記帳」父選單下，入口指向 /bookkeeping/engagement-letters/。
"""
from django.db import migrations


LETTER_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 4h11l5 5v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"/>'
    '<path d="M14 4v5h5M8 13h8M8 17h5"/></svg>'
)


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if not parent:
        return
    MenuItem.objects.update_or_create(
        title='記帳委任書',
        parent=parent,
        defaults={
            'url_name': 'bookkeeping:engagement_list',
            'icon_svg': LETTER_ICON,
            'order': 6,
            'is_active': True,
            'required_permission': '',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent:
        MenuItem.objects.filter(title='記帳委任書', parent=parent).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0020_add_onboarding_dashboard_menu'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
