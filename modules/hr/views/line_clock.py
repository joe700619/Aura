"""
Line Webhook View + 打卡模擬 View

1. LineWebhookView: 接收 Line Platform 發送的 webhook events
2. LineClockSimulateView: 在 IDE 環境中模擬 Line 打卡（用於測試）
"""

import json
import hashlib
import hmac
import base64
import logging
import requests
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib import messages

from ..services.line_clock import process_line_clock, build_reply_message

logger = logging.getLogger(__name__)


def _get_system_param(key):
    """從 SystemParameter 取得系統設定值"""
    from modules.system_config.models import SystemParameter
    try:
        return SystemParameter.objects.get(key=key).value
    except SystemParameter.DoesNotExist:
        return None


@method_decorator(csrf_exempt, name='dispatch')
class LineWebhookView(View):
    """
    接收 Line Platform 的 Webhook Events。

    員工在 Line 中傳送「打卡」文字 → 觸發打卡流程 → 回覆結果。
    """

    def post(self, request):
        # 1. 驗證簽名
        channel_secret = _get_system_param('LINE_CHANNEL_SECRET')
        if channel_secret:
            signature = request.headers.get('X-Line-Signature', '')
            body = request.body
            mac = hmac.new(
                channel_secret.encode('utf-8'),
                body,
                hashlib.sha256,
            ).digest()
            expected = base64.b64encode(mac).decode('utf-8')
            if signature != expected:
                logger.warning("Line webhook: signature mismatch")
                return HttpResponse(status=403)

        # 2. 解析 events
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        events = data.get('events', [])

        for event in events:
            if event.get('type') != 'message':
                continue
            if event.get('message', {}).get('type') != 'text':
                continue

            text = event['message']['text'].strip()
            user_id = event.get('source', {}).get('userId', '')
            reply_token = event.get('replyToken', '')

            # 判斷是否為打卡指令
            if text in ('打卡', '上班', '下班', 'clock', 'punch'):
                result = process_line_clock(user_id)
                reply_msg = build_reply_message(result)

                # 回覆訊息
                if reply_token:
                    self._reply(reply_token, [reply_msg])

        return HttpResponse(status=200)

    def _reply(self, reply_token, messages):
        """透過 Line Reply Message API 回覆"""
        access_token = _get_system_param('LINE_CHANNEL_ACCESS_TOKEN')
        if not access_token:
            logger.error("LINE_CHANNEL_ACCESS_TOKEN not configured")
            return

        url = 'https://api.line.me/v2/bot/message/reply'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        body = {
            'replyToken': reply_token,
            'messages': messages,
        }
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=5)
            if resp.status_code != 200:
                logger.error(f"Line reply failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Line reply error: {e}")


class LineClockSimulateView(LoginRequiredMixin, View):
    """
    模擬 Line 打卡（IDE 測試用）。

    GET:  顯示模擬表單
    POST: 以指定的 line_id 模擬打卡
    """

    template_name = 'attendance/line_clock_simulate.html'

    def get(self, request):
        from ..models import Employee
        employees = Employee.objects.filter(
            is_active=True, employment_status='ACTIVE'
        ).exclude(line_id='').values('id', 'name', 'line_id')

        return render(request, self.template_name, {
            'page_title': 'Line 打卡模擬',
            'employees': list(employees),
        })

    def post(self, request):
        line_id = request.POST.get('line_id', '').strip()
        manual_id = request.POST.get('line_id_manual', '').strip()
        # Manual input takes priority
        if manual_id:
            line_id = manual_id
        if not line_id:
            messages.error(request, '請選擇員工或輸入 Line ID。')
            return redirect('hr:line_clock_simulate')

        result = process_line_clock(line_id)

        if result.success:
            messages.success(request, result.message)
        else:
            messages.warning(request, result.message)

        return redirect('hr:line_clock_simulate')
