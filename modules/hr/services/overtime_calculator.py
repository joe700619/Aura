"""
加班費計算（依勞基法級距加權）

做法：把單日加班分鐘數，依「加班類別」逐級距換算成「加權分鐘」，
再以 平日每小時工資額 × 加權分鐘 / 60 算出加班費。
跨級距（例如平日加班超過 2 小時）會自動拆算，不需人工拆單。

加班類別「依加班日期自動判定」(classify_overtime_day)：
- WorkCalendar 標記國定假日 → 國定假日
- WorkCalendar 標記補班日   → 平日
- 週六（無特殊紀錄）        → 休息日
- 週日（無特殊紀錄）        → 例假
- 週一~五（無特殊紀錄）     → 平日

級距倍率為「平日每小時工資額」的總倍數（已與使用者確認）。
如需調整級距或倍率，改 TIER_TABLE 一處即可。
"""

from decimal import Decimal, ROUND_HALF_UP

# ── 加班類別 ────────────────────────────────────────────────
WEEKDAY = 'weekday'          # 平日
REST_DAY = 'rest_day'        # 休息日（通常週六）
HOLIDAY = 'holiday'          # 國定假日
REGULAR_OFF = 'regular_off'  # 例假（通常週日，原則不得加班）

DAY_TYPE_LABELS = {
    WEEKDAY: '平日',
    REST_DAY: '休息日',
    HOLIDAY: '國定假日',
    REGULAR_OFF: '例假',
}

# ── 級距表 ──────────────────────────────────────────────────
# 每個類別為 [(該級距「累計上限分鐘」, 倍率), ...]；最後一段用 None 表示無上限。
# 120 分 = 2 小時、480 分 = 8 小時。
TIER_TABLE = {
    WEEKDAY: [
        (120, Decimal('1.34')),   # 前 2 小時
        (None, Decimal('1.67')),  # 逾 2 小時
    ],
    REST_DAY: [
        (120, Decimal('1.34')),   # 前 2 小時
        (480, Decimal('1.67')),   # 2~8 小時
        (None, Decimal('2.67')),  # 逾 8 小時
    ],
    HOLIDAY: [
        (480, Decimal('2.00')),   # 8 小時內
        (None, Decimal('2.67')),  # 逾 8 小時
    ],
    REGULAR_OFF: [
        (480, Decimal('2.00')),   # 8 小時內
        (None, Decimal('2.67')),  # 逾 8 小時
    ],
}


def classify_overtime_day(d) -> str:
    """依加班日期自動判定加班類別，回傳上方常數之一。"""
    from ..models import WorkCalendar
    rec = WorkCalendar.objects.filter(date=d).first()
    if rec:
        if rec.day_type == 'national_holiday':
            return HOLIDAY
        if rec.day_type == 'makeup_workday':
            return WEEKDAY
    weekday = d.weekday()  # 0=Mon ... 5=Sat, 6=Sun
    if weekday == 6:
        return REGULAR_OFF
    if weekday == 5:
        return REST_DAY
    return WEEKDAY


def weighted_minutes(day_type: str, total_minutes) -> Decimal:
    """把加班分鐘依該類別的級距換算成「加權分鐘」。"""
    total = Decimal(total_minutes)
    if total <= 0:
        return Decimal('0')

    tiers = TIER_TABLE.get(day_type, TIER_TABLE[WEEKDAY])
    weighted = Decimal('0')
    prev_cap = Decimal('0')
    remaining = total

    for cap, multiplier in tiers:
        if remaining <= 0:
            break
        if cap is None:
            segment = remaining
        else:
            tier_span = Decimal(cap) - prev_cap
            segment = min(remaining, tier_span)
            prev_cap = Decimal(cap)
        weighted += segment * multiplier
        remaining -= segment

    return weighted


def calculate_overtime_pay(hourly_rate, day_type: str, total_minutes) -> int:
    """加班費 = 時薪 × 加權分鐘 / 60，四捨五入到元。"""
    wm = weighted_minutes(day_type, total_minutes)
    pay = Decimal(hourly_rate) * wm / Decimal('60')
    return int(pay.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
