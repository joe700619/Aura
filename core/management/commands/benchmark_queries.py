"""
壓測 list view 對應的 ORM 查詢，量測 SQL 數與時間。

測試項目模擬主要列表頁、搜尋情境，不需要登入流程。
"""
import time

from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.conf import settings


def measure(description, query_callable):
    """執行 callable，回傳 (elapsed_ms, sql_count, result_count)"""
    settings.DEBUG = True  # 必要：connection.queries 才會記錄
    reset_queries()
    t0 = time.perf_counter()
    result = query_callable()
    # 強制執行（list() 觸發 evaluation）
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
    help = 'Benchmark 主要列表頁查詢效能'

    def handle(self, *args, **options):
        from modules.basic_data.models import Customer, Contact
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.billing import ClientBill
        from modules.case_management.models import Case, Inquiry
        from modules.internal_accounting.models.receivable import Receivable
        from modules.hr.models import Employee
        from django.db.models import Count, Q, Prefetch
        from modules.bookkeeping.models.billing import ServiceFee
        from datetime import date

        tests = []

        # =================================================================
        # 客戶搜尋（驗證 Customer.tax_id / name 的 db_index）
        # =================================================================
        tests.append(measure(
            'Customer 列表（無搜尋，前 25 筆）',
            lambda: Customer.objects.filter(is_deleted=False).order_by('-created_at')[:25]
        ))
        tests.append(measure(
            'Customer 搜尋 tax_id (icontains)',
            lambda: Customer.objects.filter(tax_id__icontains='15000')[:25]
        ))
        tests.append(measure(
            'Customer 搜尋 name (icontains)',
            lambda: Customer.objects.filter(name__icontains='公司')[:25]
        ))

        # =================================================================
        # BookkeepingClient（驗證 acceptance_status / billing_status index）
        # =================================================================
        tests.append(measure(
            'BookkeepingClient 列表 (active)',
            lambda: BookkeepingClient.objects
                .filter(is_deleted=False, acceptance_status='active')
                .select_related('customer')
                .order_by('name')[:25]
        ))
        tests.append(measure(
            'BookkeepingClient 計數 (按 acceptance_status 群組)',
            lambda: BookkeepingClient.objects.values('acceptance_status').annotate(c=Count('id'))
        ))

        # =================================================================
        # ClientBill（驗證 status index 與複合 (status, -created_at)）
        # =================================================================
        tests.append(measure(
            'ClientBill 列表（按 status filter + 排序）',
            lambda: ClientBill.objects
                .filter(status='draft')
                .select_related('client')
                .order_by('-created_at')[:25]
        ))
        tests.append(measure(
            'ClientBill 按年月排序',
            lambda: ClientBill.objects
                .select_related('client')
                .order_by('-year', '-month')[:25]
        ))
        tests.append(measure(
            'ClientBill 計數 (按 status)',
            lambda: ClientBill.objects.values('status').annotate(c=Count('id'))
        ))

        # =================================================================
        # Case（驗證 status, last_activity_at index）
        # =================================================================
        tests.append(measure(
            'Case 列表 (open + ordering)',
            lambda: Case.objects.filter(status='open').order_by('-last_activity_at')[:25]
        ))
        tests.append(measure(
            'Case 計數 (按 status)',
            lambda: Case.objects.values('status').annotate(c=Count('id'))
        ))

        # =================================================================
        # Inquiry
        # =================================================================
        tests.append(measure(
            'Inquiry 列表 (status filter)',
            lambda: Inquiry.objects.filter(status='new').order_by('-created_at')[:25]
        ))
        tests.append(measure(
            'Inquiry 搜尋 (跨欄位 OR)',
            lambda: Inquiry.objects.filter(
                Q(name__icontains='王') | Q(email__icontains='王') | Q(company__icontains='王')
            )[:25]
        ))
        tests.append(measure(
            'Inquiry 計數 (按 status, 用 annotate)',
            lambda: Inquiry.objects.values('status').annotate(c=Count('id'))
        ))

        # =================================================================
        # Receivable（驗證 company_name / unified_business_no index）
        # =================================================================
        tests.append(measure(
            'Receivable 列表',
            lambda: Receivable.objects.order_by('-created_at')[:25]
        ))
        tests.append(measure(
            'Receivable 搜尋 company_name',
            lambda: Receivable.objects.filter(company_name__icontains='公司')[:25]
        ))

        # =================================================================
        # 月結批次模擬（_get_clients_for_batch 修過的 N+1）
        # =================================================================
        def _batch_simulate():
            today = date.today()
            active_fee_qs = ServiceFee.objects.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today)
            ).order_by('-effective_date')
            clients = (
                BookkeepingClient.objects
                .filter(is_deleted=False, billing_status='billing')
                .select_related('bookkeeping_assistant')
                .prefetch_related(Prefetch('service_fees', queryset=active_fee_qs, to_attr='_active_fees'))
                .order_by('name')
            )
            count = 0
            for client in clients:
                _ = client._active_fees[0] if client._active_fees else None
                count += 1
            return count
        tests.append(measure('月結批次模擬 (5K 客戶, 修過 N+1)', _batch_simulate))

        # =================================================================
        # 列印結果
        # =================================================================
        self.stdout.write('\n' + '=' * 90)
        self.stdout.write(f'{"測試項目":<55} {"時間 (ms)":>10} {"SQL":>5} {"筆數":>10}')
        self.stdout.write('=' * 90)
        for desc, elapsed, sql_count, result_count in tests:
            time_color = self.style.SUCCESS if elapsed < 100 else (
                self.style.WARNING if elapsed < 500 else self.style.ERROR
            )
            sql_color = self.style.SUCCESS if sql_count <= 3 else (
                self.style.WARNING if sql_count <= 15 else self.style.ERROR
            )
            self.stdout.write(
                f'{desc:<55} '
                f'{time_color(f"{elapsed:>9.1f}")} '
                f'{sql_color(f"{sql_count:>4}")} '
                f'{result_count:>10}'
            )
        self.stdout.write('=' * 90)
        self.stdout.write('\n判定標準:')
        self.stdout.write('  時間: < 100ms 綠 / 100-500ms 黃 / > 500ms 紅')
        self.stdout.write('  SQL : ≤ 3 綠 / 4-15 黃 / > 15 紅')
