"""每日執行：記帳客戶 onboarding 斷點 SLA 催促。

掃描「簽約後遲未指派」與「指派後遲未首次聯繫」的客戶，彙整成 digest
寄給記帳組長 / 助理 / （逾期升級）合夥人。與 ScheduledJob 連動記錄執行狀態。
手動測試：docker compose exec web python manage.py send_onboarding_sla_reminders --dry-run
"""
import logging
import traceback

from django.core.management.base import BaseCommand

from modules.bookkeeping.services.onboarding_sla import run

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '掃描記帳 onboarding 逾期未指派/未聯繫的客戶，發送 SLA 催促 digest'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只掃描並列出會通知誰，不真的寄送（測試用）',
        )

    def _record_status(self, success: bool, message: str):
        from core.models import ScheduledJob
        try:
            job = ScheduledJob.objects.filter(
                command='send_onboarding_sla_reminders'
            ).first()
            if job:
                job.record_run(success=success, message=message)
        except Exception as e:
            logger.warning('更新 ScheduledJob 狀態失敗: %s', e)

    def handle(self, *args, **opts):
        dry_run = opts.get('dry_run', False)
        try:
            result = run(dry_run=dry_run)
        except Exception as e:
            tb = traceback.format_exc()
            self.stderr.write(f'執行失敗：{e}')
            if not dry_run:
                self._record_status(False, tb)
            raise

        prefix = '【試跑，未實際寄送】' if dry_run else ''
        msg = (
            f"{prefix}逾期未指派 {result['assign_overdue']} 件、"
            f"逾期未聯繫 {result['contact_overdue']} 件；"
            f"通知 {result['recipients']} 位收件人（送出 {result['sent']} 封）。"
        )
        if result['no_lead']:
            msg += "\n⚠️『記帳組長』群組無成員或不存在——未指派案無人收到提醒。"
        if result['no_partner']:
            msg += "\n⚠️『合夥人』群組無成員或不存在——升級提醒無人收到。"
        if result['details']:
            msg += "\n收件明細：\n" + "\n".join(
                f"  - {email}: 未指派 {a} / 未聯繫 {c}"
                for email, a, c in result['details']
            )

        self.stdout.write(self.style.SUCCESS(msg))
        if not dry_run:
            self._record_status(True, msg)
