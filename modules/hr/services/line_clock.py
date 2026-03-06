"""
Line 打卡服務

處理 Line Webhook 收到的打卡訊息：
1. 從 Line user ID 比對 Employee.line_id → 找到員工
2. 判斷上班/下班（若今天還沒打卡 → 上班；若已有上班 → 下班）
3. 建立或更新 AttendanceRecord
4. 回覆打卡結果訊息
"""

import logging
from datetime import date, time
from django.utils import timezone
from ..models import Employee, AttendanceRecord

logger = logging.getLogger(__name__)


class LineClockResult:
    """打卡結果物件"""

    def __init__(self, success: bool, message: str, employee_name: str = '',
                 clock_type: str = '', clock_time: str = ''):
        self.success = success
        self.message = message
        self.employee_name = employee_name
        self.clock_type = clock_type  # 'in' or 'out'
        self.clock_time = clock_time


def process_line_clock(line_user_id: str) -> LineClockResult:
    """
    處理 Line 打卡。

    Args:
        line_user_id: Line 使用者 ID（來自 webhook event source userId）

    Returns:
        LineClockResult 包含打卡結果
    """
    # 1. 用 line_id 找到員工
    try:
        employee = Employee.objects.get(line_id=line_user_id, is_active=True)
    except Employee.DoesNotExist:
        logger.warning(f"Line clock: 找不到對應員工, line_user_id={line_user_id}")
        return LineClockResult(
            success=False,
            message="❌ 找不到您的員工資料，請確認您的 Line ID 已綁定。",
        )
    except Employee.MultipleObjectsReturned:
        logger.error(f"Line clock: 多位員工有相同 line_id={line_user_id}")
        return LineClockResult(
            success=False,
            message="❌ 系統錯誤：有多位員工綁定相同的 Line ID。",
        )

    today = timezone.localdate()
    now = timezone.localtime().time()

    # 2. 查找今天的出勤紀錄
    record = AttendanceRecord.objects.filter(
        employee=employee, date=today, is_deleted=False
    ).first()

    if record is None:
        # 還沒有紀錄 → 上班打卡
        record = AttendanceRecord.objects.create(
            employee=employee,
            date=today,
            clock_in=now,
            source='line',
        )
        clock_time_str = now.strftime("%H:%M")
        logger.info(f"Line clock-in: {employee.name} at {clock_time_str}")
        return LineClockResult(
            success=True,
            message=f"✅ {employee.name}，上班打卡成功！\n🕐 時間：{clock_time_str}",
            employee_name=employee.name,
            clock_type='in',
            clock_time=clock_time_str,
        )

    elif record.clock_in and not record.clock_out:
        # 已有上班紀錄、還沒下班 → 下班打卡
        record.clock_out = now
        record.save(update_fields=['clock_out'])
        clock_time_str = now.strftime("%H:%M")
        clock_in_str = record.clock_in.strftime("%H:%M")
        logger.info(f"Line clock-out: {employee.name} at {clock_time_str}")
        return LineClockResult(
            success=True,
            message=(
                f"✅ {employee.name}，下班打卡成功！\n"
                f"🕐 上班：{clock_in_str}\n"
                f"🕐 下班：{clock_time_str}"
            ),
            employee_name=employee.name,
            clock_type='out',
            clock_time=clock_time_str,
        )

    else:
        # 上下班都打過了
        clock_in_str = record.clock_in.strftime("%H:%M") if record.clock_in else '-'
        clock_out_str = record.clock_out.strftime("%H:%M") if record.clock_out else '-'
        return LineClockResult(
            success=False,
            message=(
                f"⚠️ {employee.name}，您今日已完成打卡。\n"
                f"🕐 上班：{clock_in_str}\n"
                f"🕐 下班：{clock_out_str}"
            ),
            employee_name=employee.name,
        )


def build_reply_message(result: LineClockResult) -> dict:
    """
    把 LineClockResult 轉成 Line Messaging API 的 reply message payload。

    Returns:
        dict suitable for Line Reply Message API body
    """
    return {
        "type": "text",
        "text": result.message,
    }
