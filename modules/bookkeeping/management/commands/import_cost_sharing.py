"""
匯入公費分攤明細到 BookkeepingClient.cost_sharing_data (JSON 欄位)。

公費分攤不是獨立 table，而是存在記帳客戶的一個 JSON 陣列裡，
每個分攤人是一個 dict：{employee_id, employee_name, task_description, ratio, amount}。
因此 import/export 那套（一欄一值）做不來——這支指令把同一統編的多列
聚合成一包 JSON，寫回對應客戶。

來源 Excel（第一列為中文表頭，一列一個分攤人）：
    統一編號 | 員工編號 | 執行項目 | 比例

員工以「員工編號」反查，存進 JSON 的 employee_id 是 Employee 的 pk（字串），
與前端公費分攤表格、員工搜尋帶回的值一致。amount 一律存 0，
實際金額由表單/帳單開啟時依服務費用 × 比例即時重算。

Usage:
    python manage.py import_cost_sharing 公費分攤.xlsx --dry-run   # 只驗證
    python manage.py import_cost_sharing 公費分攤.xlsx             # 正式寫入

注意：員工編號若在 Excel 被讀成數字，可能掉前導 0（001→1）而對不到人。
請先把該欄在 Excel 設成「文字」格式，或用 --dry-run 確認無「找不到員工編號」。
"""
import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.bookkeeping.models import BookkeepingClient
from modules.hr.models import Employee

REQUIRED_HEADERS = ['統一編號', '員工編號', '執行項目', '比例']


class Command(BaseCommand):
    help = '從 Excel 匯入公費分攤明細，聚合成 JSON 寫回記帳客戶'

    def add_arguments(self, parser):
        parser.add_argument('xlsx_path', help='來源 Excel 路徑')
        parser.add_argument('--dry-run', action='store_true',
                            help='只解析與驗證，不寫入資料庫')

    def handle(self, *args, **options):
        path = options['xlsx_path']
        dry_run = options['dry_run']

        try:
            wb = openpyxl.load_workbook(path, data_only=True)
        except FileNotFoundError:
            raise CommandError(f'找不到檔案：{path}')
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise CommandError('Excel 是空的')

        header = [self._clean(c) for c in rows[0]]
        col = {}
        for name in REQUIRED_HEADERS:
            if name not in header:
                raise CommandError(f'缺少欄位「{name}」（目前表頭：{header}）')
            col[name] = header.index(name)

        # 員工編號 → (pk 字串, 姓名)
        emp_map = {
            e.employee_number: (str(e.id), e.name)
            for e in Employee.objects.exclude(employee_number__isnull=True)
                                     .exclude(employee_number='')
        }

        grouped = {}   # tax_id -> [share dict, ...]
        errors = []
        for r_no, raw in enumerate(rows[1:], start=2):
            tax_id = self._cell(raw, col['統一編號'])
            emp_no = self._cell(raw, col['員工編號'])
            task = self._cell(raw, col['執行項目'])
            ratio_raw = self._cell(raw, col['比例'])

            if not tax_id and not emp_no and not task and not ratio_raw:
                continue  # 整列空白

            if not tax_id:
                errors.append(f'第 {r_no} 列：缺統一編號')
                continue
            if not emp_no:
                errors.append(f'第 {r_no} 列：缺員工編號')
                continue
            if emp_no not in emp_map:
                errors.append(f'第 {r_no} 列：找不到員工編號「{emp_no}」')
                continue
            try:
                ratio = float(ratio_raw) if ratio_raw else 0
            except ValueError:
                errors.append(f'第 {r_no} 列：比例非數字「{ratio_raw}」')
                continue

            emp_id, emp_name = emp_map[emp_no]
            grouped.setdefault(tax_id, []).append({
                'employee_id': emp_id,
                'employee_name': emp_name,
                'task_description': task,
                'ratio': ratio,
                'amount': 0,
            })

        # 對照記帳客戶
        clients = {
            c.tax_id: c
            for c in BookkeepingClient.objects.filter(
                tax_id__in=list(grouped.keys()), is_deleted=False)
        }
        for tax_id in grouped:
            if tax_id not in clients:
                errors.append(f'統一編號「{tax_id}」：系統查無記帳客戶')

        total_lines = sum(len(v) for v in grouped.values())
        self.stdout.write(
            f'解析完成：{len(grouped)} 個客戶、共 {total_lines} 列分攤明細')

        if errors:
            self.stdout.write(self.style.ERROR(f'發現 {len(errors)} 個問題：'))
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  - {e}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('--dry-run：未寫入任何資料'))
            return

        if errors:
            raise CommandError('有錯誤，已中止寫入。請修正後重跑（建議先 --dry-run 確認）。')

        updated = 0
        with transaction.atomic():
            for tax_id, share_rows in grouped.items():
                client = clients[tax_id]
                client.cost_sharing_data = share_rows
                client.save(update_fields=['cost_sharing_data'])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'完成：更新 {updated} 個客戶的公費分攤'))

    @staticmethod
    def _clean(value):
        return str(value).strip() if value is not None else ''

    @classmethod
    def _cell(cls, raw, i):
        return cls._clean(raw[i]) if i < len(raw) else ''
