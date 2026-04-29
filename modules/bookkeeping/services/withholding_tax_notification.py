"""
Withholding Tax Notification Service
=====================================
Sends Line/Email notifications for withholding tax filing requests.
"""
import logging

from core.notifications.services import EmailService, LineService

logger = logging.getLogger(__name__)

LINE_TEMPLATE_CODE = 'withholding_tax_notification'
EMAIL_TEMPLATE_CODE = 'withholding_tax_notification'


def build_withholding_tax_context(withholding, request=None):
    """Build the template context for a withholding tax notification."""
    client = withholding.year_record.client
    return {
        'client_name': client.name,
        'year': withholding.year_record.year,
        'payable_tax': int(withholding.payable_tax or 0),
        'tax_deadline': withholding.tax_deadline.strftime('%Y/%m/%d') if withholding.tax_deadline else '（未設定）',
        'payment_method': withholding.get_payment_method_display() if withholding.payment_method else '（未設定）',
    }


def send_withholding_tax_notification(withholding, request=None):
    """
    Send withholding tax notification to the client.
    Returns a dict: {'success_channels': [...], 'error_channels': [...]}
    """
    client = withholding.year_record.client
    notification_method = client.notification_method

    context = build_withholding_tax_context(withholding, request)
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