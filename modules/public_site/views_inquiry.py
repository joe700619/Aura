"""對外網站 — 諮詢表單接收端點。

職責：
1. 驗證輸入（含 honeypot、長度上限、Email/Phone 格式）
2. Rate limit（每 IP 每分鐘最多 5 次）
3. 寫入 Inquiry
4. 回傳 LINE 加好友連結讓前端跳轉
"""
import json
import re
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from modules.case_management.models import Inquiry


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RATE_LIMIT_PER_MIN = 5


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

    Inquiry.objects.create(
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

    return JsonResponse({"ok": True, "redirect": settings.LINE_OA_URL})
