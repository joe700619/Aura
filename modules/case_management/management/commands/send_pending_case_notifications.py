"""消化案件管理排隊中的 Email 通知。

排程建議：每 1-5 分鐘執行一次
  Windows 工作排程器 / cron:
    python manage.py send_pending_case_notifications
"""
from django.core.management.base import BaseCommand

from modules.case_management.notify_service import send_pending_notifications


class Command(BaseCommand):
    help = '送出排隊中的案件管理 Email 通知'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=200,
                            help='單次處理的最大筆數（預設 200）')

    def handle(self, *args, **opts):
        sent, failed, skipped = send_pending_notifications(limit=opts['limit'])
        msg = f'sent={sent} failed={failed} skipped={skipped}'
        if failed:
            self.stdout.write(self.style.WARNING(msg))
        else:
            self.stdout.write(self.style.SUCCESS(msg))
