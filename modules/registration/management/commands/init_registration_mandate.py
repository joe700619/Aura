"""初始化「公司登記委任書」所需資料：

  1. RegistrationMandateTemplate v1（骨架條款，status=active）— 內容由所內之後在後台改
  2. Email 邀請範本（寄簽署連結給客戶）
  3. LINE 邀請範本（推簽署連結給客戶）
  4. Email / LINE 簽署完成回執範本

重跑安全（get_or_create，不覆寫已改內容）。部署後必須執行，否則工作台無法發送、
通知會靜默失敗（同稿本確認的 init_draft_confirmation）。
"""
from django.core.management.base import BaseCommand


# 骨架條款：含常用佔位符，所內之後在 admin 依既有委任書內容覆蓋。
# 報價明細表由客戶頁固定版位顯示，本文不必（也不建議）自己排表格。
TEMPLATE_BODY = """\
<p>立委任書人 <strong>{{ company_name }}</strong>{% if unified_business_no %}（統一編號：{{ unified_business_no }}）{% endif %}（以下簡稱委任人），
茲委任本事務所辦理公司登記事宜（{{ case_types|default:"如委辦內容所列" }}），雙方議定條款如下：</p>
<ol>
  <li>委任範圍：如「委辦費用明細」所列之各項服務項目。</li>
  <li>委辦報酬：服務費用合計新台幣 <strong>{{ service_fee_total }}</strong> 元整；規費及代墊款項（{{ advance_total }} 元）依實際發生數計收，明細詳如費用明細表。</li>
  <li>委任人應提供辦理登記所需之文件與資料，並確保其內容真實無誤。</li>
  <li>本委任自委任人簽署本委任書之日起生效，至本案登記辦竣為止。</li>
  <li>本委任關係之終止、變更，應由雙方另行議定。</li>
</ol>
<p style="color:#666; font-size:13px;">（本條款為系統預設骨架，請所內依既有委任書內容於後台修訂後再啟用。）</p>
"""

EMAIL_SUBJECT = '【{{ company_name }}】公司登記委任書 — 請線上確認並簽署'

EMAIL_BODY = """\
<html><body style="font-family:'Microsoft JhengHei',Arial,sans-serif;color:#333;line-height:1.7;">
<p>您好，</p>
<p>感謝您選擇本所辦理 <strong>{{ company_name }}</strong> 的公司登記。</p>
<p>請點擊以下連結，線上閱覽委任條款與費用明細，並於頁面手寫簽名完成委任確認：</p>
<p style="margin:20px 0;">
  <a href="{{ public_url }}" style="background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">閱覽並簽署委任書</a>
</p>
<p style="color:#888;font-size:12px;">若按鈕無法點擊，請複製此連結：<br>{{ public_url }}</p>
<p style="color:#888;font-size:12px;">本連結將於 {{ expires_at|date:"Y-m-d H:i" }} 到期。本通知為系統自動發送，請勿直接回覆。</p>
</body></html>
"""

LINE_TEXT = """\
【{{ company_name }} 公司登記委任書】
本所已備妥委任書，請您線上閱覽條款與費用明細，並手寫簽名完成委任確認：
{{ public_url }}
（連結於 {{ expires_at|date:"Y-m-d H:i" }} 到期）"""


# ── 簽署完成後寄給客戶的「確認回執」（留證據：對方信箱/LINE 也有一份）──────
RECEIPT_EMAIL_SUBJECT = '【{{ company_name }}】公司登記委任書簽署完成通知'

RECEIPT_EMAIL_BODY = """\
<html><body style="font-family:'Microsoft JhengHei',Arial,sans-serif;color:#333;line-height:1.7;">
<p>{{ signer_name }} 您好，</p>
<p>本所已收到您對 <strong>{{ company_name }}</strong> 公司登記委任書的線上簽署，委任關係已成立。</p>
<ul>
  <li>簽署時間：{{ signed_at|date:"Y-m-d H:i" }}</li>
</ul>
<p>本所將據以辦理後續登記作業。如需檢視您已簽署的委任書內容：</p>
<p style="margin:16px 0;"><a href="{{ public_url }}" style="color:#2563eb;">檢視委任書</a></p>
<p style="color:#a0332a;font-size:13px;">※ 若這不是您本人的操作，請立即與本所聯繫。</p>
<p style="color:#888;font-size:12px;">本通知為系統自動發送，請勿直接回覆。</p>
</body></html>
"""

RECEIPT_LINE_TEXT = """\
【{{ company_name }} 委任書簽署完成】
已收到您於 {{ signed_at|date:"Y-m-d H:i" }} 簽署的公司登記委任書，本所將據以辦理後續登記作業。
檢視委任書：{{ public_url }}
※ 若非您本人操作，請立即與本所聯繫。"""


class Command(BaseCommand):
    help = '初始化登記委任書 v1 範本與 Email / LINE 邀請、回執範本（不覆寫已存在的）'

    def handle(self, *args, **opts):
        from core.notifications.models import EmailTemplate, LineMessageTemplate
        from modules.registration.models import RegistrationMandateTemplate

        tpl, created = RegistrationMandateTemplate.objects.get_or_create(
            version=1,
            defaults={
                'title': '公司登記委任書',
                'body_html': TEMPLATE_BODY,
                'status': RegistrationMandateTemplate.Status.ACTIVE,
                'notes': '系統初始骨架版',
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"委任書範本 v1：{'建立' if created else '已存在 — 略過'}"
        ))

        email_tpl, e_created = EmailTemplate.objects.get_or_create(
            code='registration_mandate_invite',
            defaults={
                'name': '登記委任書簽署邀請',
                'subject': EMAIL_SUBJECT,
                'body_html': EMAIL_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Email 範本：{'建立' if e_created else '已存在 — 略過'}：{email_tpl.code}"
        ))

        line_tpl, l_created = LineMessageTemplate.objects.get_or_create(
            code='registration_mandate_invite',
            defaults={
                'name': '登記委任書簽署邀請',
                'message_type': 'text',
                'text_content': LINE_TEXT,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"LINE 範本：{'建立' if l_created else '已存在 — 略過'}：{line_tpl.code}"
        ))

        receipt_email, re_created = EmailTemplate.objects.get_or_create(
            code='registration_mandate_receipt',
            defaults={
                'name': '登記委任書簽署回執',
                'subject': RECEIPT_EMAIL_SUBJECT,
                'body_html': RECEIPT_EMAIL_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Email 回執範本：{'建立' if re_created else '已存在 — 略過'}：{receipt_email.code}"
        ))

        receipt_line, rl_created = LineMessageTemplate.objects.get_or_create(
            code='registration_mandate_receipt',
            defaults={
                'name': '登記委任書簽署回執',
                'message_type': 'text',
                'text_content': RECEIPT_LINE_TEXT,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"LINE 回執範本：{'建立' if rl_created else '已存在 — 略過'}：{receipt_line.code}"
        ))
