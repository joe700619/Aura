"""
勞務報酬單繳費提醒服務
======================
每月1號掃描各客戶上個月支付、尚未繳納的勞務報酬單，
若有需扣繳稅款或補充保費，依客戶通知偏好（Email/LINE）匯總提醒。
"""
import logging
import datetime
from decimal import Decimal

from django.utils import timezone

from core.notifications.services import EmailService, LineService
from modules.bookkeeping.models import ServiceRemuneration

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE_CODE = 'service_remuneration_payment_reminder'
LINE_TEMPLATE_CODE = 'service_remuneration_payment_reminder'


def find_pending_records_for_client(client, target_month: datetime.date):
    """
    找出該客戶在 target_month 月份支付、仍未繳納、且有需繳款項的勞報單。
    繳款條件：扣繳稅款 > 0 OR 補充保費 > 0
    """
    return ServiceRemuneration.objects.filter(
        client=client,
        is_deleted=False,
        filing_date__year=target_month.year,
        filing_date__month=target_month.month,
        payment_status=ServiceRemuneration.PaymentStatus.UNPAID,
    ).exclude(
        withholding_tax=Decimal('0'),
        supplementary_premium=Decimal('0'),
    ).order_by('filing_date', 'recipient_name')


def build_context(client, records, target_month: datetime.date):
    """組裝通知內容用 context"""
    deadline_year = target_month.year if target_month.month < 12 else target_month.year + 1
    deadline_month = target_month.month + 1 if target_month.month < 12 else 1
    deadline = datetime.date(deadline_year, deadline_month, 10)

    items = []
    total_wh = Decimal('0')
    total_supp = Decimal('0')
    for r in records:
        items.append({
            'recipient_name': r.recipient_name,
            'amount': int(r.amount or 0),
            'withholding_tax': int(r.withholding_tax or 0),
            'supplementary_premium': int(r.supplementary_premium or 0),
            'category': r.get_income_category_display(),
            'filing_date': r.filing_date.strftime('%Y/%m/%d') if r.filing_date else '',
        })
        total_wh += r.withholding_tax or 0
        total_supp += r.supplementary_premium or 0

    return {
        'client_name': client.name,
        'target_year': target_month.year,
        'target_month': target_month.month,
        'deadline': deadline.strftime('%Y/%m/%d'),
        'count': len(items),
        'items': items,
        'total_withholding_tax': int(total_wh),
        'total_supplementary_premium': int(total_supp),
        'total_payable': int(total_wh + total_supp),
    }


def send_reminder_for_client(client, target_month: datetime.date):
    """
    對單一客戶發送提醒。回傳 (sent: bool, channels: list[str], errors: list[str])
    """
    if not getattr(client, 'service_remuneration_reminder_enabled', True):
        return False, [], ['客戶未啟用勞報提醒']

    records = list(find_pending_records_for_client(client, target_month))
    if not records:
        return False, [], []  # 無待繳項目，不通知

    context = build_context(client, records, target_month)
    method = client.notification_method or ''
    sent_channels, errors = [], []

    if method in ('email', 'both'):
        if client.email:
            ok = EmailService.send_email(EMAIL_TEMPLATE_CODE, [client.email], context)
            (sent_channels if ok else errors).append('Email')
        else:
            errors.append('Email（無 email 地址）')

    if method in ('line', 'both'):
        line_id = client.line_id or client.room_id
        if line_id:
            ok = LineService.send_message(LINE_TEMPLATE_CODE, line_id, context)
            (sent_channels if ok else errors).append('LINE')
        else:
            errors.append('LINE（未綁定）')

    if not method:
        errors.append('未設定通知方式')

    return bool(sent_channels), sent_channels, errors


def run_monthly_reminders(target_month: datetime.date = None) -> dict:
    """
    執行每月勞報繳費提醒掃描。
    target_month: 指定要掃描的月份（預設為上個月）
    回傳: {'total_clients': int, 'notified': int, 'errors': [(client_name, reason), ...]}
    """
    from modules.bookkeeping.models.bookkeeping_client import BookkeepingClient

    if target_month is None:
        today = timezone.localdate()
        first_of_this_month = today.replace(day=1)
        target_month = first_of_this_month - datetime.timedelta(days=1)
        target_month = target_month.replace(day=1)

    clients = BookkeepingClient.objects.filter(
        is_deleted=False,
        service_remuneration_reminder_enabled=True,
    )

    notified = 0
    errors = []
    for client in clients:
        try:
            sent, channels, client_errors = send_reminder_for_client(client, target_month)
            if sent:
                notified += 1
                logger.info(f"勞報提醒已寄送給 {client.name}：{channels}")
            for err in client_errors:
                errors.append((client.name, err))
        except Exception as e:
            logger.error(f"send_reminder_for_client failed for {client.name}: {e}")
            errors.append((client.name, str(e)))

    return {
        'total_clients': clients.count(),
        'notified': notified,
        'errors': errors,
        'target_month': target_month.strftime('%Y-%m'),
    }
