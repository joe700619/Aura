"""案件管理共用 helpers / 對外 service"""
from datetime import timedelta


GROUPING_WINDOW = timedelta(minutes=5)


def mark_inquiry_converted(inquiry_id):
    """把潛在客戶標記為已成交（供其他模組於委任成立時呼叫）。

    跨 module 寫 Inquiry 一律走這支，不讓他模組直接操作 Inquiry.objects。
    idempotent：已成交則不動。回傳是否有更新。
    """
    from .models import Inquiry
    updated = Inquiry.objects.filter(pk=inquiry_id).exclude(
        status=Inquiry.Status.CONVERTED
    ).update(status=Inquiry.Status.CONVERTED)
    return bool(updated)


def annotate_reply_display(replies):
    """為對話列表附加顯示用屬性：

    - show_date_header: 跟前一則不同日 → 顯示日期分隔線
    - is_grouped: 跟前一則同作者、5 分鐘內 → 隱藏頭像/署名（連續訊息合併）
    """
    prev = None
    last_date = None
    for r in replies:
        r_date = r.created_at.date()
        r.show_date_header = (r_date != last_date)
        last_date = r_date

        r.is_grouped = (
            prev is not None
            and not r.is_system_log
            and not prev.is_system_log
            and prev.author_type == r.author_type
            and prev.author_user_id == r.author_user_id
            and (r.created_at - prev.created_at) <= GROUPING_WINDOW
            and not r.show_date_header
        )
        prev = r
    return replies
