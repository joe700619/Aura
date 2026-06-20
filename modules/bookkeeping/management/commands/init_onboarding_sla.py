"""初始化記帳 onboarding SLA 催促所需資料：

  1. Django Group：記帳組長 / 合夥人（admin 指派成員，決定誰收提醒）
  2. ScheduledJob 紀錄（admin 可看上次執行狀態）
  3. Email digest 範本（不覆寫 admin 已改過的內容）

重跑安全（get_or_create / update_or_create）；包成 migration 讓部署自動執行。
"""
from django.core.management.base import BaseCommand


EMAIL_SUBJECT = '【記帳交接提醒】{{ today }}　待指派 {{ assign_count }} 件 / 待聯繫 {{ contact_count }} 件'

EMAIL_BODY = """\
<html>
<body style="font-family: 'Microsoft JhengHei', Arial, sans-serif; color: #333; line-height: 1.7;">
<p>{{ recipient_name }} 您好，</p>
<p>以下記帳客戶卡在交接流程，請儘快處理（紅色為已逾 7 天，請優先）：</p>

{% if assign_items %}
<h3 style="margin:16px 0 6px;">一、待指派記帳助理（{{ assign_count }} 件）</h3>
<table style="border-collapse: collapse; width: 100%; font-size: 14px;">
  <thead><tr style="background:#f0f0f0;">
    <th style="border:1px solid #ccc; padding:6px 10px;">客戶</th>
    <th style="border:1px solid #ccc; padding:6px 10px;">統編</th>
    <th style="border:1px solid #ccc; padding:6px 10px; text-align:right;">已等待天數</th>
  </tr></thead>
  <tbody>
  {% for i in assign_items %}
    <tr{% if i.escalated %} style="color:#cc0000; font-weight:bold;"{% endif %}>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ i.name }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ i.tax_id }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">{{ i.days_overdue }} 天{% if i.escalated %}（逾期）{% endif %}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endif %}

{% if contact_items %}
<h3 style="margin:16px 0 6px;">二、已指派、待首次聯繫客戶（{{ contact_count }} 件）</h3>
<table style="border-collapse: collapse; width: 100%; font-size: 14px;">
  <thead><tr style="background:#f0f0f0;">
    <th style="border:1px solid #ccc; padding:6px 10px;">客戶</th>
    <th style="border:1px solid #ccc; padding:6px 10px;">統編</th>
    <th style="border:1px solid #ccc; padding:6px 10px;">記帳助理</th>
    <th style="border:1px solid #ccc; padding:6px 10px; text-align:right;">指派後天數</th>
  </tr></thead>
  <tbody>
  {% for i in contact_items %}
    <tr{% if i.escalated %} style="color:#cc0000; font-weight:bold;"{% endif %}>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ i.name }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ i.tax_id }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ i.assistant }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">{{ i.days_overdue }} 天{% if i.escalated %}（逾期）{% endif %}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p style="color:#666; font-size:13px;">提醒：發出前置收料連結（或填上聯繫客戶日期）即可停止本提醒。</p>
{% endif %}

<p style="color:#888; font-size:12px;">本通知為系統每日自動發送，請勿直接回覆。</p>
</body>
</html>
"""


class Command(BaseCommand):
    help = '初始化記帳 onboarding SLA 的 Group / ScheduledJob / Email 範本（不覆寫已存在的範本）'

    def handle(self, *args, **opts):
        from django.conf import settings
        from django.contrib.auth.models import Group
        from core.models import ScheduledJob
        from core.notifications.models import EmailTemplate

        for name in (
            getattr(settings, 'ONBOARDING_SLA_GROUP_LEAD_GROUP', 'management'),
            getattr(settings, 'ONBOARDING_SLA_PARTNER_GROUP', 'CPA'),
        ):
            _, created = Group.objects.get_or_create(name=name)
            self.stdout.write(self.style.SUCCESS(
                f"群組：{'建立' if created else '沿用既有'}：{name}"
            ))

        job, created = ScheduledJob.objects.update_or_create(
            command='send_onboarding_sla_reminders',
            defaults={
                'name': '記帳交接 SLA 催促',
                'description': '每日掃描記帳 onboarding 遲未指派/遲未首次聯繫的客戶，發 digest 給組長/助理/合夥人',
                'cron_schedule': '30 9 * * *',
                'enabled': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"ScheduledJob：{'建立' if created else '更新'}：{job.name}"
        ))

        tpl, created = EmailTemplate.objects.get_or_create(
            code='bookkeeping_onboarding_sla_digest',
            defaults={
                'name': '記帳交接 SLA 催促 digest',
                'subject': EMAIL_SUBJECT,
                'body_html': EMAIL_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Email 範本：{'建立' if created else '已存在 — 略過'}：{tpl.code}"
        ))
