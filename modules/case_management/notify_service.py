"""消化 CaseNotificationLog 排隊中的 Email 通知"""
import logging

from django.conf import settings
from django.utils import timezone

from core.notifications.services import EmailService

from .models import Case, CaseAccessToken, CaseNotificationLog

logger = logging.getLogger(__name__)


TEMPLATE_MAP = {
    (CaseNotificationLog.Event.NEW_CASE,      'internal'): 'CASE_NEW_INTERNAL',
    (CaseNotificationLog.Event.NEW_CASE,      'external'): 'CASE_NEW_EXTERNAL',
    (CaseNotificationLog.Event.NEW_REPLY,     'internal'): 'CASE_REPLY_INTERNAL',
    (CaseNotificationLog.Event.NEW_REPLY,     'external'): 'CASE_REPLY_EXTERNAL',
    (CaseNotificationLog.Event.STATUS_CHANGE, 'internal'): 'CASE_STATUS_INTERNAL',
    (CaseNotificationLog.Event.STATUS_CHANGE, 'external'): 'CASE_STATUS_EXTERNAL',
    (CaseNotificationLog.Event.FOLLOWUP_DUE,  'internal'): 'CASE_FOLLOWUP_DUE',
}


def get_site_url():
    return getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')


def _audience(log):
    return 'internal' if log.recipient_user_id else 'external'


def _build_context(log):
    case: Case = log.case
    site = get_site_url()
    ctx = {
        'case_title': case.title,
        'case_status': case.get_status_display(),
        'case_category': case.get_category_display(),
        'case_priority': case.get_priority_display(),
        'case_summary': case.summary or '',
        'owner_name': case.owner.get_full_name() or case.owner.username,
        'external_contact_name': case.external_contact_name or '客戶',
        'followup_date': case.next_followup_date.strftime('%Y-%m-%d') if case.next_followup_date else '',
    }
    if _audience(log) == 'internal':
        u = log.recipient_user
        ctx['recipient_name'] = u.get_full_name() if u else '使用者'
        if not ctx['recipient_name']:
            ctx['recipient_name'] = u.username if u else '使用者'
        ctx['case_url'] = f"{site}/cases/{case.id}/"
    else:
        ctx['recipient_name'] = log.recipient_email
        token = (case.access_tokens
                 .filter(email=log.recipient_email, revoked_at__isnull=True,
                         expires_at__gt=timezone.now())
                 .first())
        if not token:
            token = CaseAccessToken.issue(case=case, email=log.recipient_email)
        ctx['case_url'] = f"{site}/cases/access/{token.token}/"

    if log.event == CaseNotificationLog.Event.NEW_REPLY:
        last = (case.replies.filter(is_system_log=False, is_deleted=False)
                .order_by('-created_at').first())
        if last:
            content = last.content or ''
            ctx['last_author'] = last.author_display_name or '對方'
            ctx['last_content'] = content[:300] + ('...' if len(content) > 300 else '')
    return ctx


def send_pending_notifications(limit=200):
    """處理 status=QUEUED 且 channel=EMAIL 的紀錄。回傳 (sent, failed, skipped)"""
    qs = (CaseNotificationLog.objects
          .filter(status=CaseNotificationLog.Status.QUEUED,
                  channel=CaseNotificationLog.Channel.EMAIL,
                  is_deleted=False)
          .select_related('case', 'case__owner', 'recipient_user')
          .order_by('created_at')[:limit])

    sent = failed = skipped = 0
    for log in qs:
        recipient = log.recipient_email or (log.recipient_user.email if log.recipient_user else '')
        if not recipient:
            log.status = CaseNotificationLog.Status.SKIPPED
            log.error_message = 'no recipient email'
            log.save(update_fields=['status', 'error_message', 'updated_at'])
            skipped += 1
            continue

        template_code = TEMPLATE_MAP.get((log.event, _audience(log)))
        if not template_code:
            log.status = CaseNotificationLog.Status.SKIPPED
            log.error_message = f'no template for {log.event}/{_audience(log)}'
            log.save(update_fields=['status', 'error_message', 'updated_at'])
            skipped += 1
            continue

        try:
            ctx = _build_context(log)
            ok = EmailService.send_email(template_code, [recipient], ctx)
            if ok:
                log.status = CaseNotificationLog.Status.SENT
                log.sent_at = timezone.now()
                sent += 1
            else:
                log.status = CaseNotificationLog.Status.FAILED
                log.error_message = 'EmailService returned False (template missing or render error)'
                failed += 1
        except Exception as e:
            log.status = CaseNotificationLog.Status.FAILED
            log.error_message = f'{type(e).__name__}: {e}'[:500]
            failed += 1
            logger.exception('Failed to send case notification log %s', log.id)
        log.save(update_fields=['status', 'sent_at', 'error_message', 'updated_at'])

    return sent, failed, skipped
