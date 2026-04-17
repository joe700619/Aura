"""
Provisional Tax Notification Service
=====================================
Sends Line/Email notifications for provisional tax payment requests.
"""
import logging

from core.notifications.services import EmailService, LineService

logger = logging.getLogger(__name__)

LINE_TEMPLATE_CODE = 'provisional_tax_notification'
EMAIL_TEMPLATE_CODE = 'provisional_tax_notification'


def build_provisional_tax_context(provisional, request=None):
    """Build the template context for a provisional tax notification."""
    client = provisional.year_record.client
    return {
        'client_name': client.name,
        'year': provisional.year_record.year,
        'provisional_amount': int(provisional.provisional_amount or 0),
        'tax_deadline': provisional.tax_deadline.strftime('%Y/%m/%d') if provisional.tax_deadline else '（未設定）',
        'payment_method': provisional.get_payment_method_display() or '（未設定）',
    }


def send_provisional_tax_notification(provisional, request=None):
    """
    Send provisional tax notification to the client.
    Returns a dict: {'success_channels': [...], 'error_channels': [...]}
    """
    client = provisional.year_record.client
    setting = getattr(client, 'income_tax_setting', None)
    notification_method = getattr(setting, 'notification_method', None)

    context = build_provisional_tax_context(provisional, request)
    results = {'success_channels': [], 'error_channels': []}

    send_email = notification_method in ('email', 'both')
    send_line = notification_method in ('line', 'both')

    if send_email:
        email = client.email
        if email:
            ok = EmailService.send_email(EMAIL_TEMPLATE_CODE, [email], context)
            if ok:
                results['success_channels'].append('Email')
            else:
                results['error_channels'].append('Email')
        else:
            results['error_channels'].append('Email（無email地址）')

    if send_line:
        line_id = client.line_id or client.room_id
        if line_id:
            ok = LineService.send_message(LINE_TEMPLATE_CODE, line_id, context)
            if ok:
                results['success_channels'].append('Line')
            else:
                results['error_channels'].append('Line')
        else:
            results['error_channels'].append('Line（無 Line ID）')

    if not send_email and not send_line:
        results['error_channels'].append('未設定通知方式')

    return results