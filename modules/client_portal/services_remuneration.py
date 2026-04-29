import logging

from django.conf import settings as django_settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.template.loader import render_to_string
from django.urls import reverse

from modules.system_config.helpers import get_system_param

logger = logging.getLogger(__name__)


def send_confirmation_email(request, obj) -> bool:
    """寄送勞務報酬單確認信給所得人。"""
    confirm_path = reverse('client_portal:service_remuneration_confirm', kwargs={'token': obj.confirm_token})
    confirm_url = request.build_absolute_uri(confirm_path)

    context = {
        'obj': obj,
        'confirm_url': confirm_url,
        'company_name': obj.company_name or obj.client.name,
    }
    subject = f"【{context['company_name']}】勞務報酬單確認 - {obj.recipient_name}"
    body_html = render_to_string('client_portal/email/service_remuneration_confirm.html', context)

    host = get_system_param('EMAIL_HOST', '')
    from_email = get_system_param('DEFAULT_FROM_EMAIL', getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'))

    if host:
        port = int(get_system_param('EMAIL_PORT', 587))
        smtp_user = get_system_param('EMAIL_HOST_USER', '')
        smtp_pass = get_system_param('EMAIL_HOST_PASSWORD', '')
        use_tls = str(get_system_param('EMAIL_USE_TLS', 'True')).lower() == 'true'
        connection = SMTPBackend(
            host=host, port=port,
            username=smtp_user, password=smtp_pass,
            use_tls=use_tls, fail_silently=False,
        )
    else:
        connection = get_connection(fail_silently=False)

    try:
        from modules.client_portal.pdf_service_remuneration import generate_service_remuneration_pdf
        pdf_bytes = generate_service_remuneration_pdf(obj)
        filing_str = (obj.filing_date or obj.created_at.date()).strftime('%Y%m%d')
        pdf_filename = f"勞務報酬單_{obj.recipient_name}_{filing_str}.pdf"
    except Exception as e:
        logger.warning(f'PDF 產生失敗（仍繼續寄信）: {e}')
        pdf_bytes = None
        pdf_filename = None

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[obj.recipient_email],
            connection=connection,
        )
        msg.attach_alternative(body_html, 'text/html')
        if pdf_bytes:
            msg.attach(pdf_filename, pdf_bytes, 'application/pdf')
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f'send_confirmation_email failed: {e}')
        return False
