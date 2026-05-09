import base64
import logging

from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def send_confirmation_email(request, obj) -> bool:
    """
    寄送勞務報酬單確認信給所得人（非同步）。

    PDF 在 request thread 中產生（CPU-bound 但快），實際寄信走 celery
    讓使用者按下「寄送」立刻得到回應。
    """
    confirm_path = reverse('client_portal:service_remuneration_confirm', kwargs={'token': obj.confirm_token})
    confirm_url = request.build_absolute_uri(confirm_path)

    context = {
        'obj': obj,
        'confirm_url': confirm_url,
        'company_name': obj.company_name or obj.client.name,
    }
    subject = f"【{context['company_name']}】勞務報酬單確認 - {obj.recipient_name}"
    body_html = render_to_string('client_portal/email/service_remuneration_confirm.html', context)

    # 產 PDF（同步）
    attachments = []
    try:
        from modules.client_portal.pdf_service_remuneration import generate_service_remuneration_pdf
        pdf_bytes = generate_service_remuneration_pdf(obj)
        filing_str = (obj.filing_date or obj.created_at.date()).strftime('%Y%m%d')
        attachments.append({
            'filename': f'勞務報酬單_{obj.recipient_name}_{filing_str}.pdf',
            'content_b64': base64.b64encode(pdf_bytes).decode('ascii'),
            'mimetype': 'application/pdf',
        })
    except Exception as e:
        logger.warning(f'PDF 產生失敗（仍繼續寄信）: {e}')

    # 寄信（非同步）
    from core.tasks import send_email_async
    send_email_async.delay(
        subject=subject,
        body_html=body_html,
        recipients=[obj.recipient_email],
        attachments_b64=attachments,
    )
    return True
