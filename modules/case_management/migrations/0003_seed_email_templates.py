"""Seed 7 個案件管理用 EmailTemplate"""
from django.db import migrations


TEMPLATES = [
    {
        'code': 'CASE_NEW_INTERNAL',
        'name': '案件管理 — 新案件（給內部）',
        'subject': '[案件] 新案件：{{ case_title }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>客戶 {{ external_contact_name }} 透過 Portal 建立了新案件：</p>
<table style="border-collapse:collapse;margin:12px 0;">
  <tr><td style="padding:4px 12px 4px 0;color:#666;">案件標題</td><td><strong>{{ case_title }}</strong></td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#666;">類別</td><td>{{ case_category }}</td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#666;">優先度</td><td>{{ case_priority }}</td></tr>
</table>
{% if case_summary %}<p style="background:#f5f5f5;padding:10px;border-radius:6px;white-space:pre-line;">{{ case_summary }}</p>{% endif %}
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">前往處理 →</a></p>
""",
    },
    {
        'code': 'CASE_NEW_EXTERNAL',
        'name': '案件管理 — 新案件（給客戶）',
        'subject': '[案件] 案件已建立：{{ case_title }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>{{ owner_name }} 為您建立了新案件，後續溝通請從下方連結進入：</p>
<table style="border-collapse:collapse;margin:12px 0;">
  <tr><td style="padding:4px 12px 4px 0;color:#666;">案件標題</td><td><strong>{{ case_title }}</strong></td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#666;">負責會計師</td><td>{{ owner_name }}</td></tr>
</table>
{% if case_summary %}<p style="background:#f5f5f5;padding:10px;border-radius:6px;white-space:pre-line;">{{ case_summary }}</p>{% endif %}
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">查看案件 →</a></p>
<p style="color:#888;font-size:12px;">此連結為您專屬的安全存取連結，請勿轉寄他人。</p>
""",
    },
    {
        'code': 'CASE_REPLY_INTERNAL',
        'name': '案件管理 — 新回覆（給內部）',
        'subject': '[案件] 客戶回覆：{{ case_title }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>客戶 <strong>{{ last_author }}</strong> 在案件「{{ case_title }}」中留言：</p>
<blockquote style="border-left:4px solid #10b981;padding:10px 16px;margin:12px 0;background:#ecfdf5;white-space:pre-line;">{{ last_content }}</blockquote>
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">查看並回覆 →</a></p>
""",
    },
    {
        'code': 'CASE_REPLY_EXTERNAL',
        'name': '案件管理 — 新回覆（給客戶）',
        'subject': '[案件] 會計師回覆：{{ case_title }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>會計師 <strong>{{ last_author }}</strong> 在案件「{{ case_title }}」中回覆：</p>
<blockquote style="border-left:4px solid #4f46e5;padding:10px 16px;margin:12px 0;background:#eef2ff;white-space:pre-line;">{{ last_content }}</blockquote>
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">查看並回覆 →</a></p>
""",
    },
    {
        'code': 'CASE_STATUS_INTERNAL',
        'name': '案件管理 — 狀態變更（給內部）',
        'subject': '[案件] 狀態變更：{{ case_title }} → {{ case_status }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>案件「{{ case_title }}」狀態已變更為：<strong>{{ case_status }}</strong></p>
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">查看案件 →</a></p>
""",
    },
    {
        'code': 'CASE_STATUS_EXTERNAL',
        'name': '案件管理 — 狀態變更（給客戶）',
        'subject': '[案件] 案件狀態更新：{{ case_title }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>您的案件「{{ case_title }}」狀態已更新為：<strong>{{ case_status }}</strong></p>
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">查看案件 →</a></p>
""",
    },
    {
        'code': 'CASE_FOLLOWUP_DUE',
        'name': '案件管理 — 追蹤日到期（給內部）',
        'subject': '[案件] 追蹤日到期：{{ case_title }}',
        'body_html': """
<p>您好 {{ recipient_name }}，</p>
<p>以下案件已到追蹤日期，請評估是否需採取動作：</p>
<table style="border-collapse:collapse;margin:12px 0;">
  <tr><td style="padding:4px 12px 4px 0;color:#666;">案件標題</td><td><strong>{{ case_title }}</strong></td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#666;">當前狀態</td><td>{{ case_status }}</td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#666;">追蹤日</td><td>{{ followup_date }}</td></tr>
</table>
<p><a href="{{ case_url }}" style="display:inline-block;background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">查看案件 →</a></p>
""",
    },
]


def seed(apps, _):
    EmailTemplate = apps.get_model('core', 'EmailTemplate')
    for t in TEMPLATES:
        EmailTemplate.objects.update_or_create(
            code=t['code'],
            defaults={
                'name': t['name'],
                'subject': t['subject'],
                'body_html': t['body_html'].strip(),
                'is_active': True,
            },
        )


def unseed(apps, _):
    EmailTemplate = apps.get_model('core', 'EmailTemplate')
    EmailTemplate.objects.filter(code__in=[t['code'] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('case_management', '0002_seed_menu_item'),
        ('core', '0003_emailtemplate_emaillog'),
    ]
    operations = [migrations.RunPython(seed, unseed)]
