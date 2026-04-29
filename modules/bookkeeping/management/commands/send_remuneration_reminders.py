"""
每月1號執行：發送勞務報酬單繳費提醒。
與 ScheduledJob 連動，執行後會更新 last_run_at / last_status / last_message。
"""
import datetime
import logging
import traceback

from django.core.management.base import BaseCommand

from modules.bookkeeping.services.service_remuneration_notification import run_monthly_reminders

logger = logging.getLogger(__name__)

JOB_NAME = '勞務報酬繳費提醒'


class Command(BaseCommand):
    help = '掃描上個月支付的勞務報酬單，對未繳款的客戶發送 Email/LINE 提醒'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='YYYY-MM 指定掃描月份（預設為上個月）',
        )

    def _record_status(self, success: bool, message: str):
        from core.models import ScheduledJob
        try:
            job = ScheduledJob.objects.filter(command='send_remuneration_reminders').first()
            if job:
                job.record_run(success=success, message=message)
        except Exception as e:
            logger.warning(f'更新 ScheduledJob 狀態失敗: {e}')

    def handle(self, *args, **opts):
        target_month = None
        if opts.get('month'):
            try:
                target_month = datetime.datetime.strptime(opts['month'], '%Y-%m').date()
            except ValueError:
                self.stderr.write(f"--month 格式錯誤：{opts['month']}（需 YYYY-MM）")
                self._record_status(False, f"參數錯誤：{opts['month']}")
                return

        try:
            result = run_monthly_reminders(target_month=target_month)
        except Exception as e:
            tb = traceback.format_exc()
            self.stderr.write(f'執行失敗：{e}')
            self._record_status(False, tb)
            raise

        msg = (
            f"掃描月份 {result['target_month']}：共 {result['total_clients']} 位客戶，"
            f"成功通知 {result['notified']} 位。"
        )
        if result['errors']:
            msg += f"\n錯誤：\n" + "\n".join(f"  - {n}: {r}" for n, r in result['errors'])

        self.stdout.write(self.style.SUCCESS(msg))
        self._record_status(True, msg)
