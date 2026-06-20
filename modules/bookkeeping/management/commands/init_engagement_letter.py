"""初始化記帳委任書所需資料：

  1. EngagementLetterTemplate v1（骨架條款，status=active）— 內容由所內之後用既有委任書改
  2. Email 邀請範本（寄委任書連結給客戶）

重跑安全（get_or_create，不覆寫已改內容）；包成 migration 讓部署自動執行。
"""
from django.core.management.base import BaseCommand


# 骨架條款：含全部佔位符，所內之後在 admin 用既有委任書內容覆蓋。
TEMPLATE_BODY = """\
<p>立委任書人 <strong>{{ company_name }}</strong>（統一編號：{{ tax_id }}，以下簡稱委任人），
茲委任本事務所辦理記帳及稅務申報服務，雙方議定條款如下：</p>
<ol>
  <li>委任服務自 <strong>{{ engagement_start_date }}</strong> 起生效。</li>
  <li>服務報酬：每月新台幣 <strong>{{ service_fee }}</strong> 元整（{{ pricing_type }}），依「{{ billing_cycle }}」收取。{{ fee_note }}</li>
  <li>委任人應依約定期限提供記帳所需之憑證、發票及相關資料。</li>
  <li>本委任關係之終止、變更，應由雙方另行議定。</li>
</ol>
<p style="color:#666; font-size:13px;">（本條款為系統預設骨架，請所內依既有委任書內容於後台修訂後再啟用。）</p>
"""

EMAIL_SUBJECT = '【{{ company_name }}】記帳服務委任書 — 請線上確認'

EMAIL_BODY = """\
<html><body style="font-family:'Microsoft JhengHei',Arial,sans-serif;color:#333;line-height:1.7;">
<p>{{ contact_name }} 您好，</p>
<p>感謝您選擇本事務所辦理 <strong>{{ company_name }}</strong> 的記帳服務。</p>
<p>請點擊以下連結，線上閱覽委任條款並確認委任：</p>
<p style="margin:20px 0;">
  <a href="{{ public_url }}" style="background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">閱覽並確認委任書</a>
</p>
<p style="color:#888;font-size:12px;">若按鈕無法點擊，請複製此連結：<br>{{ public_url }}</p>
<p style="color:#888;font-size:12px;">本通知為系統自動發送，請勿直接回覆。</p>
</body></html>
"""


class Command(BaseCommand):
    help = '初始化記帳委任書 v1 範本與邀請 Email 範本（不覆寫已存在的）'

    def handle(self, *args, **opts):
        from modules.bookkeeping.models import EngagementLetterTemplate
        from core.notifications.models import EmailTemplate

        tpl, created = EngagementLetterTemplate.objects.get_or_create(
            version=1,
            defaults={
                'title': '記帳服務委任書',
                'body_html': TEMPLATE_BODY,
                'status': EngagementLetterTemplate.Status.ACTIVE,
                'notes': '系統初始骨架版',
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"委任書範本 v1：{'建立' if created else '已存在 — 略過'}"
        ))

        email_tpl, e_created = EmailTemplate.objects.get_or_create(
            code='bookkeeping_engagement_letter_invite',
            defaults={
                'name': '記帳委任書邀請',
                'subject': EMAIL_SUBJECT,
                'body_html': EMAIL_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Email 範本：{'建立' if e_created else '已存在 — 略過'}：{email_tpl.code}"
        ))
