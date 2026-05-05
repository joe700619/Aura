"""案件管理共用 helpers"""
from datetime import timedelta


GROUPING_WINDOW = timedelta(minutes=5)


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
