"""新增「交接儀表板」側選單（記帳交接收件匣，組長保險絲）。

掛在「記帳」父選單下，入口指向 /bookkeeping/onboarding/。
"""
from django.db import migrations


DASHBOARD_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 13h8V3H3v10Zm10 8h8V3h-8v18ZM3 21h8v-6H3v6Z"/></svg>'
)


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if not parent:
        return  # 防呆：父層不存在就跳過
    MenuItem.objects.update_or_create(
        title='交接儀表板',
        parent=parent,
        defaults={
            'url_name': 'bookkeeping:onboarding_dashboard',
            'icon_svg': DASHBOARD_ICON,
            'order': 5,
            'is_active': True,
            'required_permission': '',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent:
        MenuItem.objects.filter(title='交接儀表板', parent=parent).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0019_add_inquiry_menu'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
