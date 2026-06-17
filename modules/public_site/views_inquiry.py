"""對外網站 — 諮詢表單接收端點。

職責：
1. 驗證輸入（含 honeypot、長度上限、Email/Phone 格式）
2. Rate limit（每 IP 每分鐘最多 5 次）
3. 寫入 Inquiry
4. 寄送通知信給事務所（非同步，不卡 request）
5. 回傳 LINE 加好友連結讓前端跳轉
"""
import json
import logging
import re
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from modules.case_management.models import Inquiry

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RATE_LIMIT_PER_MIN = 5


def _notify_staff(inquiry, request):
    """送出諮詢後，非同步寄通知信給事務所。未設定收件信箱則略過。

    收件信箱在 admin「系統參數設定」的 INQUIRY_NOTIFY_EMAIL 設定（多個用逗號分隔），
    未設則 fallback 到 settings.INQUIRY_NOTIFY_EMAIL（env）。
    """
    from modules.system_config.helpers import get_system_param
    raw = get_system_param('INQUIRY_NOTIFY_EMAIL', default='') or ''
    recipients = [e.strip() for e in raw.split(',') if e.strip()]
    if not recipients:
        return

    try:
        detail_path = reverse('case_management:inquiry_detail', args=[inquiry.pk])
        detail_url = request.build_absolute_uri(detail_path)
    except Exception:
        detail_url = ''

    source_label = inquiry.get_source_display()
    rows = [
        ('姓名', inquiry.name),
        ('Email', inquiry.email),
        ('電話', inquiry.phone),
        ('公司', inquiry.company),
        ('事業階段', inquiry.stage),
        ('來源', source_label),
    ]
    rows_html = ''.join(
        f'<tr><td style="padding:4px 12px 4px 0;color:#78716c;white-space:nowrap;">{escape(label)}</td>'
        f'<td style="padding:4px 0;color:#1a1816;">{escape(value or "—")}</td></tr>'
        for label, value in rows
    )
    message_html = escape(inquiry.message or '—').replace('\n', '<br>')
    link_html = (
        f'<p style="margin:16px 0 0;"><a href="{escape(detail_url)}" '
        f'style="color:#a0332a;">前往後台查看 / 認領 →</a></p>' if detail_url else ''
    )
    body_html = (
        f'<div style="font-family:sans-serif;font-size:14px;color:#1a1816;">'
        f'<h2 style="font-size:16px;">官網收到新的{escape(source_label)}</h2>'
        f'<table style="border-collapse:collapse;font-size:14px;">{rows_html}</table>'
        f'<p style="margin:16px 0 4px;color:#78716c;">內容</p>'
        f'<div style="padding:10px 12px;background:#f2efe9;border-radius:6px;">{message_html}</div>'
        f'{link_html}</div>'
    )
    subject = f'【官網{source_label}】{inquiry.name}'

    # on_commit：等本筆 Inquiry 交易 commit 後才入列，避免 worker 搶在 commit 前查不到
    from core.tasks import send_email_async
    transaction.on_commit(
        lambda: send_email_async.delay(subject, body_html, recipients)
    )


def _client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@require_POST
@csrf_protect
def submit_inquiry(request):
    # Rate limit（簡單版：cache 計數，每分鐘）
    ip = _client_ip(request)
    if ip:
        key = f"inquiry_rl:{ip}"
        count = cache.get(key, 0)
        if count >= RATE_LIMIT_PER_MIN:
            return JsonResponse({"ok": False, "error": "too_many_requests"}, status=429)
        cache.set(key, count + 1, timeout=60)

    # 解析 payload（同時支援 form-urlencoded 與 JSON）
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
    else:
        data = request.POST

    def get(key, max_len=400):
        v = (data.get(key) or '').strip()
        return v[:max_len]

    # Honeypot — 機器人通常會把所有欄位都填，正常用戶看不到
    if get('website'):
        return JsonResponse({"ok": True, "redirect": settings.LINE_OA_URL})

    name = get('name', 100)
    email = get('email', 200)
    phone = get('phone', 40)
    company = get('company', 120)
    stage = get('stage', 40)
    message = get('message', 2000)
    source = get('source', 40) or Inquiry.Source.LANDING_CONTACT

    # 驗證
    errors = {}
    if not name:
        errors['name'] = '請填寫姓名'
    if email and not EMAIL_RE.match(email):
        errors['email'] = 'Email 格式不正確'
    if not email and not phone:
        errors['contact'] = '請至少留下 Email 或電話其中一項'
    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    inquiry = Inquiry.objects.create(
        name=name,
        email=email,
        phone=phone,
        company=company,
        stage=stage,
        message=message,
        source=source if source in dict(Inquiry.Source.choices) else Inquiry.Source.OTHER,
        referer=request.META.get('HTTP_REFERER', '')[:300],
        ip=ip or None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
    )

    _notify_staff(inquiry, request)

    return JsonResponse({
        "ok": True,
        "redirect": settings.LINE_OA_URL,
        "id": inquiry.pk,
    })
