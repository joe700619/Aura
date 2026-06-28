"""初始化「商工登記稿本確認」所需資料：

  1. Email 邀請範本（寄稿本確認連結給客戶）
  2. LINE 邀請範本（推稿本確認連結給客戶）
  3. SystemParameter『SEAL_AUTHORIZATION_TEXT』用印授權標準文字（admin 可改）

重跑安全（get_or_create，不覆寫已改內容）。
"""
from django.core.management.base import BaseCommand

from modules.registration.services import DEFAULT_SEAL_AUTHORIZATION_TEXT

EMAIL_SUBJECT = '【{{ company_name }}】登記稿本確認 — 請線上檢視並簽署'

EMAIL_BODY = """\
<html><body style="font-family:'Microsoft JhengHei',Arial,sans-serif;color:#333;line-height:1.7;">
<p>您好，</p>
<p>本所已備妥 <strong>{{ company_name }}</strong> 的商工登記稿本，正式送件前請您線上檢視確認。</p>
<p>請點擊以下連結，檢視/下載稿本並於頁面手寫簽名確認：</p>
<p style="margin:20px 0;">
  <a href="{{ public_url }}" style="background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">檢視並確認稿本</a>
</p>
<p style="color:#888;font-size:12px;">若按鈕無法點擊，請複製此連結：<br>{{ public_url }}</p>
<p style="color:#888;font-size:12px;">本連結將於 {{ expires_at|date:"Y-m-d H:i" }} 到期。本通知為系統自動發送，請勿直接回覆。</p>
</body></html>
"""

LINE_TEXT = """\
【{{ company_name }} 登記稿本確認】
本所已備妥登記稿本，正式送件前請您線上檢視並簽署確認：
{{ public_url }}
（連結於 {{ expires_at|date:"Y-m-d H:i" }} 到期）"""


class Command(BaseCommand):
    help = '初始化稿本確認的 Email / LINE 邀請範本與用印授權標準文字（不覆寫已存在的）'

    def handle(self, *args, **opts):
        from core.notifications.models import EmailTemplate, LineMessageTemplate
        from modules.system_config.models import SystemParameter

        email_tpl, e_created = EmailTemplate.objects.get_or_create(
            code='registration_draft_confirmation_invite',
            defaults={
                'name': '登記稿本確認邀請',
                'subject': EMAIL_SUBJECT,
                'body_html': EMAIL_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Email 範本：{'建立' if e_created else '已存在 — 略過'}：{email_tpl.code}"
        ))

        line_tpl, l_created = LineMessageTemplate.objects.get_or_create(
            code='registration_draft_confirmation_invite',
            defaults={
                'name': '登記稿本確認邀請',
                'message_type': 'text',
                'text_content': LINE_TEXT,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"LINE 範本：{'建立' if l_created else '已存在 — 略過'}：{line_tpl.code}"
        ))

        param, p_created = SystemParameter.objects.get_or_create(
            key='SEAL_AUTHORIZATION_TEXT',
            defaults={'value': DEFAULT_SEAL_AUTHORIZATION_TEXT},
        )
        self.stdout.write(self.style.SUCCESS(
            f"用印授權文字參數：{'建立' if p_created else '已存在 — 略過'}：{param.key}"
        ))
