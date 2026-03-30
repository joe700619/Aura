"""
VAT Notification Service
========================
Sends Line/Email notifications for VAT payment requests,
and handles the public (no-login) payment confirmation callback.
"""
import logging
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

from core.notifications.services import EmailService, LineService

logger = logging.getLogger(__name__)

# ── Template codes (set these up in the Notification admin UI) ──
EMAIL_TEMPLATE_CODE = 'vat_payment_request'
LINE_TEMPLATE_CODE = 'vat_payment_request'


def build_vat_context(period, request=None):
    """Build the Jinja2 template context for a VAT period notification."""
    client = period.year_record.client
    freq = client.tax_setting.filing_frequency if hasattr(client, 'tax_setting') else 'bimonthly'

    if freq == 'bimonthly':
        period_label = f"{period.period_start_month:02d}-{period.period_start_month + 1:02d}月"
    else:
        period_label = f"{period.period_start_month:02d}月"

    # Build the confirmation URL (public, token-based)
    confirm_path = reverse('bookkeeping:vat_confirm', kwargs={'token': str(period.confirm_token)})
    if request:
        confirm_url = request.build_absolute_uri(confirm_path)
    else:
        base = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000')
        confirm_url = f"{base}{confirm_path}"

    # Extract outstanding_balance from POST if available
    outstanding_balance = 0
    if request and request.method == 'POST':
        try:
            outstanding_balance = int(float(request.POST.get('outstanding_balance', 0)))
        except (ValueError, TypeError):
            outstanding_balance = 0

    payable_tax = int(period.payable_tax or 0)
    final_total = payable_tax + outstanding_balance

    return {
        'client_name': client.name,
        'year': period.year_record.year,
        'period_label': period_label,
        'payable_tax': payable_tax,
        'outstanding_balance': outstanding_balance,
        'final_total': final_total,
        'tax_deadline': period.tax_deadline.strftime('%Y/%m/%d') if period.tax_deadline else '（未設定）',
        'payment_method': period.get_period_payment_method_display() or '（未設定）',
        'confirm_url': confirm_url,
    }


def send_vat_notification(period, request=None):
    """
    Send VAT payment request notification to the client.
    Returns a dict: {'success': bool, 'channels': [], 'errors': []}
    """
    client = period.year_record.client
    setting = getattr(client, 'tax_setting', None)
    notification_method = getattr(setting, 'notification_method', None)

    context = build_vat_context(period, request)
    results = {'success_channels': [], 'error_channels': []}

    send_email = notification_method in ('email', 'both')
    send_line = notification_method in ('line', 'both')

    # ── Email ──
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

    # ── Line ──
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
