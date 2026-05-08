"""
模擬「修復前」的查詢方式，作為對照組。
跟 benchmark_queries 比較才能看出優化效益。
"""
import time

from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.conf import settings


def measure(description, query_callable):
    settings.DEBUG = True
    reset_queries()
    t0 = time.perf_counter()
    result = query_callable()
    if hasattr(result, '__iter__') and not isinstance(result, (list, dict, int)):
        result = list(result)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    sql_count = len(connection.queries)
    if isinstance(result, list):
        result_count = len(result)
    elif isinstance(result, int):
        result_count = result
    else:
        result_count = '?'
    return description, elapsed_ms, sql_count, result_count


class Command(BaseCommand):
    help = 'Benchmark baseline - 模擬修復前的查詢，當對照組'

    def handle(self, *args, **options):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.billing import ServiceFee
        from django.db.models import Q
        from datetime import date

        tests = []

        # =================================================================
        # 月結批次 - 修復前的 N+1 寫法（會跑 5K+ 條 SQL）
        # =================================================================
        def _batch_simulate_n_plus_1():
            today = date.today()
            clients = (
                BookkeepingClient.objects
                .filter(is_deleted=False, billing_status='billing')
                .select_related('bookkeeping_assistant')
                .prefetch_related('service_fees')  # ← 修前只是普通 prefetch
                .order_by('name')
            )
            count = 0
            for client in clients:
                # ← 修前在迴圈內 .filter() 觸發 N+1
                active_fee = (
                    client.service_fees
                    .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
                    .order_by('-effective_date')
                    .first()
                )
                count += 1
            return count
        tests.append(measure(
            '月結批次（N+1 寫法 - 修復前）',
            _batch_simulate_n_plus_1
        ))

        self.stdout.write('\n' + '=' * 90)
        self.stdout.write(f'{"測試項目":<55} {"時間 (ms)":>10} {"SQL":>5} {"筆數":>10}')
        self.stdout.write('=' * 90)
        for desc, elapsed, sql_count, result_count in tests:
            self.stdout.write(
                f'{desc:<55} {elapsed:>9.1f}  {sql_count:>4}  {result_count:>10}'
            )
        self.stdout.write('=' * 90)
