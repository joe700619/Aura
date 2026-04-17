import logging
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from modules.internal_accounting.models import Receivable, ReceivableNotification
from core.notifications.services import LineService, EmailService

logger = logging.getLogger(__name__)

# 閾值設定：天數 -> 通知管道
THRESHOLDS = [
    (30, ReceivableNotification.Channel.LINE),
    (40, ReceivableNotification.Channel.LINE),
    (50, ReceivableNotification.Channel.LINE),
    (60, ReceivableNotification.Channel.EMAIL),
]


class Command(BaseCommand):
    help = '每日執行：依逾期天數發送Line/Email催收通知'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-pk',
            type=int,
            metavar='PK',
            help='【測試用】強制對指定應收帳款 pk 發送，忽略帳齡與重複發送限制',
        )
        parser.add_argument(
            '--threshold',
            type=int,
            metavar='DAYS',
            choices=[30, 40, 50, 60],
            help='【測試用】搭配 --force-pk，只發送指定閾值（30/40/50/60）',
        )
        parser.add_argument(
            '--site-url',
            type=str,
            metavar='URL',
            help='網站根網址，例如 https://aura.example.com（優先於系統參數 SITE_BASE_URL）',
        )

    def handle(self, *args, **options):
        force_pk = options.get('force_pk')
        force_threshold = options.get('threshold')
        site_url = self._resolve_site_url(options.get('site_url'))

        # ── 測試模式 ──────────────────────────────────────────
        if force_pk:
            try:
                receivable = Receivable.objects.prefetch_related(
                    'collections', 'notifications'
                ).get(pk=force_pk)
            except Receivable.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"pk={force_pk} not found"))
                return

            thresholds = [
                (d, ch) for d, ch in THRESHOLDS
                if force_threshold is None or d == force_threshold
            ]
            self.stdout.write(self.style.WARNING(
                f"[TEST] {receivable.company_name} (pk={force_pk}), "
                f"thresholds={[d for d, _ in thresholds]}, site_url={site_url or '(none)'}"
            ))
            for threshold_days, channel in thresholds:
                success, error_msg = self._send_notice(
                    receivable, threshold_days, channel, site_url
                )
                ReceivableNotification.objects.update_or_create(
                    receivable=receivable,
                    threshold_days=threshold_days,
                    channel=channel,
                    defaults={'success': success, 'error_message': error_msg},
                )
                if success:
                    self.stdout.write(self.style.SUCCESS(
                        f"  [OK] {threshold_days}days/{channel} sent"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  [FAIL] {threshold_days}days/{channel}: {error_msg}"
                    ))
            return

        # ── 正常排程模式 ──────────────────────────────────────
        today = timezone.now().date()
        self.stdout.write(f"[{today}] starting overdue notices, site_url={site_url or '(none)'}...")

        receivables = (
            Receivable.objects.filter(is_deleted=False)
            .prefetch_related('collections', 'notifications')
        )
        pending_receivables = [r for r in receivables if r.status != '已結清']

        sent_count = 0
        skip_count = 0

        for receivable in pending_receivables:
            aging = receivable.aging

            for threshold_days, channel in THRESHOLDS:
                if aging < threshold_days:
                    continue

                already_sent = receivable.notifications.filter(
                    threshold_days=threshold_days,
                    channel=channel,
                ).exists()
                if already_sent:
                    skip_count += 1
                    continue

                success, error_msg = self._send_notice(
                    receivable, threshold_days, channel, site_url
                )

                ReceivableNotification.objects.create(
                    receivable=receivable,
                    threshold_days=threshold_days,
                    channel=channel,
                    success=success,
                    error_message=error_msg,
                )

                if success:
                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  [OK] {receivable.company_name} ({aging}d/{threshold_days}d/{channel})"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  [FAIL] {receivable.company_name} ({aging}d/{threshold_days}d/{channel}): {error_msg}"
                    ))

        self.stdout.write(f"\ndone. sent={sent_count}, skipped={skip_count}")

    def _resolve_site_url(self, cli_value):
        """優先順序：CLI 參數 > 系統參數 SITE_BASE_URL > 空字串"""
        if cli_value:
            return cli_value.rstrip('/')
        try:
            from modules.system_config.helpers import get_system_param
            val = get_system_param('SITE_BASE_URL', '')
            return val.rstrip('/') if val else ''
        except Exception:
            return ''

    def _generate_payment_url(self, receivable, site_url):
        """產生綠界付款連結，回傳 URL 字串或空字串（失敗時）"""
        if not site_url:
            return ''
        outstanding = int(receivable.outstanding_balance)
        if outstanding <= 0:
            return ''
        try:
            from modules.payment.models import PaymentTransaction
            suffix = f"{random.randint(0, 9999):04d}"
            base_no = (receivable.receivable_no or str(receivable.pk)).replace('-', '')
            merchant_trade_no = f"{base_no}{suffix}"[:20]
            PaymentTransaction.objects.create(
                merchant_trade_no=merchant_trade_no,
                total_amount=outstanding,
                trade_desc=f"AR {receivable.receivable_no or receivable.pk}",
                item_name=f"Service Fee ({receivable.company_name})"[:200],
                payment_type=PaymentTransaction.PaymentType.ECPAY,
                related_app='internal_accounting',
                related_model='Receivable',
                related_id=str(receivable.pk),
            )
            return f"{site_url}/payment/bill/{merchant_trade_no}/"
        except Exception as e:
            logger.warning(f"Failed to generate payment URL for receivable {receivable.pk}: {e}")
            return ''

    def _send_notice(self, receivable, threshold_days, channel, site_url):
        """發送單筆通知，回傳 (success: bool, error_msg: str)"""
        payment_url = self._generate_payment_url(receivable, site_url)

        context = {
            'company_name': receivable.company_name,
            'outstanding_balance': int(receivable.outstanding_balance),
            'aging': receivable.aging,
            'threshold_days': threshold_days,
            'main_contact': receivable.main_contact or '',
            'payment_url': payment_url,
        }

        try:
            if channel == ReceivableNotification.Channel.LINE:
                target_id = receivable.room_id or receivable.line_id
                if not target_id:
                    return False, "Line Room ID / Line ID not set"

                result = LineService.send_message(
                    template_code='receivable_overdue_notice',
                    line_user_id=target_id,
                    context=context,
                )
                if not result:
                    return False, "LineService failed (check LineMessageLog)"
                return True, ''

            elif channel == ReceivableNotification.Channel.EMAIL:
                if not receivable.assistant_email:
                    return False, f"assistant_email not set (assistant={receivable.assistant or 'N/A'})"

                result = EmailService.send_email(
                    template_code='receivable_overdue_60days',
                    recipients=[receivable.assistant_email],
                    context=context,
                )
                if not result:
                    return False, "EmailService failed (check EmailLog)"
                return True, ''

        except Exception as e:
            logger.exception(
                f"Exception sending notice: receivable={receivable.pk}, "
                f"threshold={threshold_days}, channel={channel}"
            )
            return False, str(e)

        return False, "unknown channel"
