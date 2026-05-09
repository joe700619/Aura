"""
Core Celery tasks。

提供通用、可被任何 module 呼叫的非同步工作。

呼叫方式：
    from core.tasks import send_email_async
    send_email_async.delay(subject, body_html, recipients)

注意：
- task 內不要 import 模組層級會引入循環的東西
- 失敗時 celery 會自動 retry（max_retries=3）
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='core.send_email_async',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 30},  # 30s 後重試
    retry_backoff=True,
)
def send_email_async(self, subject: str, body_html: str, recipients: list,
                     from_email: str = None, body_text: str = '',
                     attachments_b64: list = None) -> dict:
    """
    非同步寄信。呼叫端不必等寄送完成。

    Args:
        subject: 信件主旨
        body_html: HTML 內容
        recipients: 收件者 email list
        from_email: 寄件者 email（None 用 DEFAULT_FROM_EMAIL）
        body_text: 純文字 fallback
        attachments_b64: 附件 list，元素格式為 dict
            {'filename': 'foo.pdf', 'content_b64': '<base64-string>', 'mimetype': 'application/pdf'}
            （bytes 不能直接走 celery JSON 序列化，故用 base64）

    Returns:
        {'sent': True, 'recipients': N} on success
    """
    import base64

    if not recipients:
        return {'sent': False, 'reason': 'no recipients'}

    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    # 嘗試從 SystemParameter 讀 SMTP 設定（覆蓋 settings.py 的值）
    try:
        from modules.system_config.helpers import get_system_param
        host = get_system_param('EMAIL_HOST', getattr(settings, 'EMAIL_HOST', ''))
        if host:
            from django.core.mail.backends.smtp import EmailBackend
            connection = EmailBackend(
                host=host,
                port=int(get_system_param('EMAIL_PORT', getattr(settings, 'EMAIL_PORT', 587))),
                username=get_system_param('EMAIL_HOST_USER', getattr(settings, 'EMAIL_HOST_USER', '')),
                password=get_system_param('EMAIL_HOST_PASSWORD', getattr(settings, 'EMAIL_HOST_PASSWORD', '')),
                use_tls=str(get_system_param('EMAIL_USE_TLS', 'True')).lower() == 'true',
                fail_silently=False,
            )
        else:
            connection = get_connection(fail_silently=False)
    except Exception:
        connection = get_connection(fail_silently=False)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_text,
        from_email=from_email,
        to=recipients,
        connection=connection,
    )
    if body_html:
        msg.attach_alternative(body_html, 'text/html')

    for att in attachments_b64 or []:
        msg.attach(
            att['filename'],
            base64.b64decode(att['content_b64']),
            att.get('mimetype', 'application/octet-stream'),
        )

    msg.send(fail_silently=False)
    logger.info(f'Email sent to {recipients}: {subject!r}')
    return {'sent': True, 'recipients': len(recipients)}


@shared_task(name='core.send_email_log_async')
def send_email_log_async(log_id: int) -> dict:
    """
    非同步寄出已建立的 EmailLog。
    呼叫端先建立 EmailLog（status='pending'），然後 .delay(log.id) 觸發實際寄送。

    這個 task 走 EmailService._send_from_log，會更新 EmailLog 的 status 與 sent_at。
    """
    from core.notifications.models import EmailLog
    from core.notifications.services import EmailService

    log = EmailLog.objects.filter(pk=log_id).first()
    if not log:
        logger.warning(f'EmailLog {log_id} not found, skip')
        return {'sent': False, 'reason': 'log not found'}

    success = EmailService._send_from_log(log)
    return {'sent': success, 'log_id': log_id}


@shared_task(name='core.cleanup_old_history')
def cleanup_old_history(days: int = 365) -> dict:
    """
    清除超過指定天數的 simple-history 紀錄。
    建議 celery beat 每月排程。

    Args:
        days: 保留天數，預設 365 天（1 年）

    Returns:
        {'deleted': N, 'days': X}
    """
    from datetime import timedelta
    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    # simple-history 內建命令：清除每筆主資料超過 days 天且非最新版本的 history
    call_command('clean_old_history', '--days', str(days), '--auto', stdout=out)
    output = out.getvalue()
    logger.info(f'cleanup_old_history (days={days}):\n{output}')
    return {'days': days, 'output': output[:500]}
