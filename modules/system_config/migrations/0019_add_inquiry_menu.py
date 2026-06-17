"""
新增「諮詢預約」側選單項目（官網諮詢 / 快速登記表單的潛在客戶清單）。

獨立 top-level 項目，緊接「案件管理」之後。諮詢清單掛在 /cases/inquiries/，
原本只能從 email 連結進入，側選單沒有入口。
"""
from django.db import migrations


INQUIRY_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z"/>'
    '<path d="m3.5 6.5 8.5 6 8.5-6"/></svg>'
)


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.update_or_create(
        title='諮詢預約',
        parent=None,
        defaults={
            'url_name': 'case_management:inquiry_list',
            'icon_svg': INQUIRY_ICON,
            'order': 46,
            'is_active': True,
            'required_permission': '',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(title='諮詢預約', parent__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0018_seed_inquiry_notify_email_param'),
    ]

    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
