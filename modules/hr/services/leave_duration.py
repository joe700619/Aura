"""
請假時數計算

依公司固定上班時段，計算一段請假區間實際應扣的工作時數。

規則：
- 上班 08:30 ~ 17:30，中午 12:00 ~ 13:00 為休息（不計薪、不計假）
  → 全天上班時數 = 8 小時
- 連續請假時，逐日累計：只計工作日（週末與國定假日跳過，依 WorkCalendar），
  每日只計上班時段與請假區間的重疊，再扣掉午休
- 結果以 0.5 小時為單位四捨五入
"""

from datetime import time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

# ── 公司固定上班時段（如需調整，改這裡即可）────────────────────────────
WORK_START = time(8, 30)
WORK_END = time(17, 30)
LUNCH_START = time(12, 0)
LUNCH_END = time(13, 0)


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _overlap_minutes(seg_start: time, seg_end: time, win_start: time, win_end: time) -> int:
    """seg 與 win 兩個時段的重疊分鐘數（不重疊回傳 0）"""
    start = max(_minutes(seg_start), _minutes(win_start))
    end = min(_minutes(seg_end), _minutes(win_end))
    return max(0, end - start)


def _working_minutes_in_segment(seg_start: time, seg_end: time) -> int:
    """單日某時段內的實際工作分鐘數（落在上班時段、扣掉午休）"""
    work = _overlap_minutes(seg_start, seg_end, WORK_START, WORK_END)
    lunch = _overlap_minutes(seg_start, seg_end, LUNCH_START, LUNCH_END)
    return max(0, work - lunch)


def calculate_leave_hours(start_dt, end_dt) -> Decimal:
    """
    計算 [start_dt, end_dt] 區間應扣的請假時數。

    Args:
        start_dt: 開始時間（datetime，可為 aware）
        end_dt: 結束時間（datetime，可為 aware）

    Returns:
        Decimal 時數，以 0.5 為單位。區間無效時回傳 Decimal('0')。
    """
    if not start_dt or not end_dt or end_dt <= start_dt:
        return Decimal('0')

    # 轉成本地時間（台北），確保 .date()/.time() 取到使用者實際填的時間
    if timezone.is_aware(start_dt):
        start_dt = timezone.localtime(start_dt)
    if timezone.is_aware(end_dt):
        end_dt = timezone.localtime(end_dt)

    # 延後 import 避免模組載入循環
    from ..models import WorkCalendar

    first_date = start_dt.date()
    last_date = end_dt.date()

    total_minutes = 0
    current = first_date
    while current <= last_date:
        if WorkCalendar.is_workday(current):
            # 當日的請假時段：第一天從開始時間起、最後一天到結束時間止，
            # 中間整天則涵蓋整個上班時段
            seg_start = start_dt.time() if current == first_date else WORK_START
            seg_end = end_dt.time() if current == last_date else WORK_END
            total_minutes += _working_minutes_in_segment(seg_start, seg_end)
        current += timedelta(days=1)

    hours = Decimal(total_minutes) / Decimal(60)
    # 四捨五入到 0.5
    return (hours * 2).quantize(Decimal('1'), rounding=ROUND_HALF_UP) / 2
