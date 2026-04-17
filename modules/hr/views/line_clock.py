"""
Line 打卡模擬 View（HR 模組）

LineWebhookView 已搬移至 core/notifications/views.py（route: /core/notifications/line/webhook/）。
本檔案只保留 IDE 測試用的模擬打卡頁面。
"""

import logging
from core.mixins import HRRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

from ..services.line_clock import process_line_clock, build_reply_message

logger = logging.getLogger(__name__)


class LineClockSimulateView(HRRequiredMixin, View):
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
