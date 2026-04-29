"""
初始化勞務報酬繳費提醒所需資料：
  1. ScheduledJob 紀錄
  2. Email 通知範本（若不存在則建立）
  3. LINE 通知範本（若不存在則建立）
"""
from django.core.management.base import BaseCommand


EMAIL_DEFAULT_SUBJECT = '【勞務報酬】{{ target_year }}年{{ target_month }}月繳費提醒（共 {{ count }} 筆）'

EMAIL_DEFAULT_BODY = """\
<html>
<body style="font-family: 'Microsoft JhengHei', Arial, sans-serif; color: #333; line-height: 1.7;">
<p>{{ client_name }} 您好，</p>

<p>提醒您：以下勞務報酬單將於 <strong style="color:#cc0000;">{{ deadline }}</strong> 為扣繳稅款及補充保費繳款期限，目前尚未繳納，請儘快繳款並上傳收據。</p>

<table style="border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px;">
  <thead>
    <tr style="background:#f0f0f0;">
      <th style="border:1px solid #ccc; padding:6px 10px;">支付日期</th>
      <th style="border:1px solid #ccc; padding:6px 10px;">所得人</th>
      <th style="border:1px solid #ccc; padding:6px 10px;">類別</th>
      <th style="border:1px solid #ccc; padding:6px 10px; text-align:right;">金額</th>
      <th style="border:1px solid #ccc; padding:6px 10px; text-align:right;">扣繳稅款</th>
      <th style="border:1px solid #ccc; padding:6px 10px; text-align:right;">補充保費</th>
    </tr>
  </thead>
  <tbody>
    {% for item in items %}
    <tr>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ item.filing_date }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ item.recipient_name }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px;">{{ item.category }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">${{ item.amount }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">${{ item.withholding_tax }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">${{ item.supplementary_premium }}</td>
    </tr>
    {% endfor %}
  </tbody>
  <tfoot>
    <tr style="background:#fafafa; font-weight:bold;">
      <td colspan="4" style="border:1px solid #ccc; padding:6px 10px; text-align:right;">合計</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">${{ total_withholding_tax }}</td>
      <td style="border:1px solid #ccc; padding:6px 10px; text-align:right;">${{ total_supplementary_premium }}</td>
    </tr>
    <tr style="background:#fff4e0; font-weight:bold; color:#cc0000;">
      <td colspan="4" style="border:1px solid #ccc; padding:6px 10px; text-align:right;">應繳合計</td>
      <td colspan="2" style="border:1px solid #ccc; padding:6px 10px; text-align:right;">${{ total_payable }}</td>
    </tr>
  </tfoot>
</table>

<p>請於繳費期限前完成繳納，並至客戶端入口上傳繳款單以更新繳納狀態。</p>
<p style="color:#888; font-size:12px;">本通知為系統自動發送，請勿直接回覆。</p>
</body>
</html>
"""

LINE_DEFAULT_BODY = """【勞務報酬繳費提醒】

{{ client_name }} 您好，

您有 {{ count }} 筆 {{ target_year }}/{{ target_month }} 勞務報酬尚未繳款。
繳款期限：{{ deadline }}
應繳合計：${{ total_payable }}（扣繳 ${{ total_withholding_tax }}＋補充保費 ${{ total_supplementary_premium }}）

請儘速繳款並上傳收據。
"""


class Command(BaseCommand):
    help = '初始化勞務報酬繳費提醒所需的 ScheduledJob 與通知範本（不會覆寫已存在的範本）'

    def handle(self, *args, **opts):
        from core.models import ScheduledJob
        from core.notifications.models import EmailTemplate, LineMessageTemplate

        job, created = ScheduledJob.objects.update_or_create(
            command='send_remuneration_reminders',
            defaults={
                'name': '勞務報酬繳費提醒',
                'description': '每月1號 09:00 掃描上月支付、未繳款的勞務報酬單，發送匯總提醒給客戶',
                'cron_schedule': '0 9 1 * *',
                'enabled': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'建立' if created else '更新'} ScheduledJob：{job.name}"
        ))

        email_tpl, e_created = EmailTemplate.objects.get_or_create(
            code='service_remuneration_payment_reminder',
            defaults={
                'name': '勞務報酬繳費提醒',
                'subject': EMAIL_DEFAULT_SUBJECT,
                'body_html': EMAIL_DEFAULT_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Email 範本：{'建立' if e_created else '已存在 — 略過'}：{email_tpl.code}"
        ))

        line_tpl, l_created = LineMessageTemplate.objects.get_or_create(
            code='service_remuneration_payment_reminder',
            defaults={
                'name': '勞務報酬繳費提醒',
                'message_type': 'text',
                'text_content': LINE_DEFAULT_BODY,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"LINE 範本：{'建立' if l_created else '已存在 — 略過'}：{line_tpl.code}"
        ))
