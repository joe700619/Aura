"""每日掃描追蹤日到期的案件，把通知排入 queue。

排程建議：每天早上 09:00 跑一次
  Windows 工作排程器 / cron:
    python manage.py check_case_followups
然後讓 send_pending_case_notifications 接著消化
"""
from django.core.management.base import BaseCommand

from modules.case_management.signals import daily_followup_check


class Command(BaseCommand):
    help = '掃描追蹤日到期的案件，建立通知紀錄'

    def handle(self, *args, **opts):
        daily_followup_check()
        self.stdout.write(self.style.SUCCESS('done'))
