"""
請假單「消失資料」鑑識 Management Command（一次性查詢用）

用途：找出在資料庫主表已不存在、但歷史表還留有痕跡的請假單，
      用來釐清「請假單列表 / admin 都找不到」的那筆假單到底發生什麼事。

用法：
    python manage.py inspect_leave_history                 # 全部
    python manage.py inspect_leave_history --employee 王
    python manage.py inspect_leave_history --days 30        # 只看近 30 天的歷史事件
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.hr.models import LeaveRequest, Employee


HISTORY_TYPE_LABEL = {
    '+': '建立',
    '~': '修改',
    '-': '刪除(硬刪)',
}


class Command(BaseCommand):
    help = '鑑識請假單歷史：找出主表已消失但歷史表仍有痕跡的請假單'

    def add_arguments(self, parser):
        parser.add_argument('--employee', type=str, default=None,
                            help='只看姓名包含此字串的員工')
        parser.add_argument('--days', type=int, default=None,
                            help='只看近 N 天內的歷史事件')

    def handle(self, *args, **options):
        name_filter = options['employee']
        days = options['days']

        # 1) 主表現況（含軟刪除，不過濾，跟 admin 一致）
        live_ids = set(LeaveRequest.objects.values_list('id', flat=True))
        self.stdout.write(self.style.SUCCESS(
            f'\n=== 主表現況：目前資料庫共有 {len(live_ids)} 筆請假單 row ==='
        ))

        # 2) 歷史表全量
        history_qs = LeaveRequest.history.all().order_by('id', 'history_date')
        if days:
            since = timezone.now() - timedelta(days=days)
            history_qs = history_qs.filter(history_date__gte=since)

        # 先把員工 id -> 顯示名稱建好（含已刪員工的 fallback）
        emp_names = dict(Employee.objects.values_list('id', 'name'))

        # 依 leave request id 聚合歷史事件
        events_by_id = {}
        for h in history_qs:
            events_by_id.setdefault(h.id, []).append(h)

        # 3) 找「主表已消失」的請假單（歷史有、主表無）
        vanished_ids = sorted(set(events_by_id.keys()) - live_ids)

        self.stdout.write(self.style.WARNING(
            f'\n=== 歷史表出現過、但主表已不存在的請假單：{len(vanished_ids)} 筆 ===\n'
        ))

        if not vanished_ids:
            self.stdout.write('  （沒有消失的請假單。若你那筆假單在歷史表也查無，'
                              '代表它很可能從未成功寫入 DB，或在別的資料庫/環境。）')

        for lr_id in vanished_ids:
            events = events_by_id[lr_id]
            first = events[0]
            last = events[-1]
            emp_id = getattr(last, 'employee_id', None)
            emp_name = emp_names.get(emp_id, f'(員工已不存在 id={emp_id})')

            if name_filter and name_filter not in str(emp_name):
                continue

            emp_alive = emp_id in emp_names
            self.stdout.write(self.style.HTTP_INFO(
                f'■ 請假單 id={lr_id}　員工={emp_name}　'
                f'（員工目前{"在" if emp_alive else "已不在"}資料庫）'
            ))
            try:
                self.stdout.write(
                    f'    內容：{first.start_datetime:%Y-%m-%d %H:%M} ~ '
                    f'{first.end_datetime:%H:%M}　{first.total_hours}h　'
                    f'狀態={first.status}'
                )
            except Exception:
                pass

            for h in events:
                label = HISTORY_TYPE_LABEL.get(h.history_type, h.history_type)
                user = getattr(h, 'history_user', None)
                user_str = getattr(user, 'username', None) or '(系統/匿名)'
                self.stdout.write(
                    f'      - {h.history_date:%Y-%m-%d %H:%M:%S}　{label}　by {user_str}'
                )

            # 判讀：最後一筆若不是刪除事件，卻在主表消失 → 很可能 CASCADE 連帶刪
            if last.history_type != '-':
                self.stdout.write(self.style.WARNING(
                    '      ⚠ 歷史最後一筆不是「刪除」事件，主表卻消失了 → '
                    '高度疑似員工被硬刪除後 CASCADE 連帶清掉（此情況不會留刪除歷史）'
                ))
            self.stdout.write('')

        # 4) 順帶列出目前主表裡狀態 = cancelled 的（被前端「刪除」過的）
        cancelled = LeaveRequest.objects.filter(status='cancelled')
        self.stdout.write(self.style.SUCCESS(
            f'=== 補充：主表中狀態為「已取消」的請假單：{cancelled.count()} 筆 '
            f'（這些是前端按「刪除」但其實只是取消、row 仍在）==='
        ))
        for lr in cancelled.select_related('employee', 'leave_type')[:50]:
            self.stdout.write(
                f'  id={lr.id}　{lr.employee.name}　{lr.leave_type.name}　'
                f'{lr.start_datetime:%Y-%m-%d}　is_deleted={lr.is_deleted}'
            )
