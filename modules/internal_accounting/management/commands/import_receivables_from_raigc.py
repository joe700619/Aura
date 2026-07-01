"""
一次性匯入 raigc 未收應收帳款 → Aura。

用途：把 raigc 尚未收款的應收（約 221 筆）帶入 Aura，並逐筆產生立帳傳票草稿。
- 收據號碼原樣沿用為 receivable_no（AU=簽證 / BI=記帳 / RO=登記）。
- 全額未收 → 不建 Collection。
- 帳齡從匯入日 0 起算（不回填 created_at，避免催收排程一次轟炸）；原始帳齡寫進 remarks。
- 立帳傳票：借 1123 / 貸 收入科目（依前綴）/ 貸 2192 股東往來（代墊，方案 B）。
- 公費分攤：員工姓名 → 員工編號（EMPLOYEE_MAP）→ hr.Employee；對不到的仍建立但 employee=None 並列清單。

冪等：已存在的 receivable_no 直接跳過，可重複執行。

用法：
    python manage.py import_receivables_from_raigc <csv路徑> --dry-run       # 本機試跑，不寫入
    python manage.py import_receivables_from_raigc <csv路徑> --user <帳號>   # 正式匯入（Railway）
"""
import csv
from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from modules.internal_accounting.models import Receivable, ReceivableFeeApportion
from modules.internal_accounting.services import ReceivableTransferService

# 姓名 → 員工編號（由使用者提供，僅涵蓋本檔出現的員工）
EMPLOYEE_MAP = {
    '王姿云': '2026004', '黃勝平': '2026001', '劉珈均': '2026007', '潘昱宏': '2026013',
    '林奕廷': '2026012', '林雋樵': '2026010', '張家綾': '2026008', '王婉倫': '2026006',
    '盧彥諶': '2026015', '葉芮均': '2026016', '蕭冠伶': '2026009', '許家甄': '2026011',
    '許紘綺': '2026002', '詹怡珮': '2026003', '謝語宸': '2026014', '鄭思旻': '2026005',
    '蔡長壽': '2026017',
}

# 收據號碼前綴 → 服務費項目名稱（前綴數字決定傳票收入科目：1簽證/2記帳/3登記）
PREFIX_SERVICE_LABEL = {
    'AU': '1.00 簽證服務費',
    'BI': '2.00 記帳服務費',
    'RO': '3.00 登記服務費',
}
ADVANCE_LABEL = '9.00 代墊款項'

# 員工欄位 (姓名, 比例, 金額) 的欄位索引組
EMP_COL_GROUPS = [(13, 14, 15), (16, 17, 18), (19, 20, 21), (22, 23, 24)]


def parse_amount(raw):
    """'$190,620.' / '22,500' / '' → int"""
    if raw is None:
        return 0
    s = str(raw).strip().replace('$', '').replace(',', '').rstrip('.')
    if not s:
        return 0
    return int(round(float(s)))


def parse_ratio(raw):
    """'12.50%' → Decimal('12.50')"""
    if not raw:
        return Decimal('0')
    s = str(raw).strip().replace('%', '').replace(',', '')
    if not s:
        return Decimal('0')
    return Decimal(s)


def parse_date(raw):
    """'2026/06/01' → date；空 → None"""
    s = (raw or '').strip()
    if not s:
        return None
    return datetime.strptime(s, '%Y/%m/%d').date()


class Command(BaseCommand):
    help = '一次性匯入 raigc 未收應收帳款並逐筆產生立帳傳票草稿'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='CSV 檔路徑')
        parser.add_argument('--dry-run', action='store_true', help='只驗證與統計，不寫入資料庫')
        parser.add_argument('--user', type=str, help='傳票建立者帳號（預設取第一個 superuser）')
        parser.add_argument('--limit', type=int, help='只處理前 N 筆（測試用）')
        parser.add_argument('--encoding', type=str, help='強制指定 CSV 編碼（預設自動 utf-8-sig → big5）')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']
        limit = options.get('limit')

        rows = self._read_csv(csv_path, options.get('encoding'))
        data = rows[1:]
        if limit:
            data = data[:limit]

        user = None
        if not dry_run:
            user = self._resolve_user(options.get('user'))

        mode = 'DRY-RUN（不寫入）' if dry_run else '正式匯入'
        self.stdout.write(self.style.WARNING(f"=== {mode}｜{len(data)} 筆 ==="))

        created = skipped = errors = voucher_count = apportion_count = 0
        sum_ar = sum_service = sum_advance = 0
        unmapped_names = set()      # CSV 有名字但不在 EMPLOYEE_MAP
        missing_employees = set()   # 有編號但 DB 找不到（本機常見）
        mismatch_rows = []          # 服務費+代墊 ≠ 應收總額
        partial_rows = []           # 未收 ≠ 應收（疑似已部分收款）

        for idx, row in enumerate(data, start=2):  # 2 = 對應試算表列號（含表頭）
            if not row or not row[0].strip():
                continue
            receivable_no = row[0].strip()
            prefix = receivable_no[:2]

            service_label = PREFIX_SERVICE_LABEL.get(prefix)
            if not service_label:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  [列{idx}] 未知收據前綴 {prefix}（{receivable_no}），略過"))
                continue

            ar_total = parse_amount(row[9])
            unpaid = parse_amount(row[10])
            service_fee = parse_amount(row[11])
            advance = parse_amount(row[12])

            # 資料品質檢查
            if service_fee + advance != ar_total:
                mismatch_rows.append((receivable_no, service_fee + advance, ar_total))
            if unpaid != ar_total:
                partial_rows.append((receivable_no, unpaid, ar_total))

            sum_ar += ar_total
            sum_service += service_fee
            sum_advance += advance

            # 既有 → 跳過（冪等）
            if Receivable.objects.filter(receivable_no=receivable_no).exists():
                skipped += 1
                continue

            # 組 quotation_data
            quotation = []
            if service_fee > 0:
                quotation.append({'service_name': service_label, 'amount': service_fee, 'remark': 'raigc 匯入'})
            if advance > 0:
                quotation.append({'service_name': ADVANCE_LABEL, 'amount': advance, 'remark': 'raigc 匯入代墊款'})

            # 解析公費分攤（先算，順便統計 unmapped）
            apportions = []
            for name_c, ratio_c, amt_c in EMP_COL_GROUPS:
                name = (row[name_c].strip() if len(row) > name_c else '')
                if not name:
                    continue
                emp_no = EMPLOYEE_MAP.get(name)
                if not emp_no:
                    unmapped_names.add(name)
                apportions.append({
                    'name': name,
                    'employee_number': emp_no,
                    'ratio': parse_ratio(row[ratio_c] if len(row) > ratio_c else ''),
                    'amount': parse_amount(row[amt_c] if len(row) > amt_c else ''),
                })

            aging_raw = (row[8] or '').strip().rstrip('.')

            if dry_run:
                created += 1
                if created <= 8:
                    self._print_plan(idx, receivable_no, row[1].strip(), service_label,
                                     service_fee, advance, ar_total, apportions, missing_employees)
                else:
                    # 仍要統計 missing employees
                    self._check_employees(apportions, missing_employees)
                continue

            # ── 正式寫入（每列獨立 transaction）──
            try:
                with transaction.atomic():
                    receivable = Receivable.objects.create(
                        receivable_no=receivable_no,
                        date=parse_date(row[5]),
                        company_name=row[1].strip(),
                        unified_business_no=(row[2].strip() or None),
                        phone=(row[3].strip() or None),
                        main_contact=(row[4].strip() or None),
                        line_id=(row[6].strip() or None),
                        email=(row[7].strip() or None),
                        remarks=f"raigc 匯入；原始帳齡 {aging_raw or 'N/A'} 天",
                        quotation_data=quotation,
                    )

                    row_apportions = 0
                    for ap in apportions:
                        emp = self._get_employee(ap['employee_number'], missing_employees)
                        ReceivableFeeApportion.objects.create(
                            receivable=receivable,
                            employee=emp,
                            task_description=('' if emp else f"[未對應] {ap['name']}"),
                            ratio=ap['ratio'],
                            amount=ap['amount'],
                        )
                        row_apportions += 1

                    voucher = ReceivableTransferService.generate_voucher_for_receivable(receivable, user)

                # transaction 成功 commit 後才累計，避免 rollback 的列被算進去
                created += 1
                apportion_count += row_apportions
                if voucher:
                    voucher_count += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  [列{idx}] {receivable_no} 匯入失敗：{e}"))

        self._print_summary(dry_run, created, skipped, errors, voucher_count, apportion_count,
                            sum_ar, sum_service, sum_advance, unmapped_names, missing_employees,
                            mismatch_rows, partial_rows)

    # ───────────────────────── helpers ─────────────────────────
    def _read_csv(self, path, forced_enc):
        encodings = [forced_enc] if forced_enc else ['utf-8-sig', 'big5']
        last_err = None
        for enc in encodings:
            try:
                with open(path, encoding=enc, newline='') as f:
                    rows = list(csv.reader(f))
                if rows and len(rows[0]) >= 25:
                    self.stdout.write(f"讀檔成功（encoding={enc}，{len(rows) - 1} 筆）")
                    return rows
            except (UnicodeDecodeError, LookupError) as e:
                last_err = e
            except FileNotFoundError:
                raise CommandError(f"找不到檔案：{path}")
        raise CommandError(f"無法解析 CSV（試過 {encodings}）：{last_err}")

    def _resolve_user(self, username):
        User = get_user_model()
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                raise CommandError(f"找不到帳號：{username}")
            return user
        user = User.objects.filter(is_superuser=True).order_by('id').first()
        if not user:
            raise CommandError("找不到 superuser，請用 --user 指定傳票建立者")
        return user

    def _get_employee(self, emp_no, missing_set):
        if not emp_no:
            return None
        from modules.hr.models.employee import Employee
        emp = Employee.objects.filter(employee_number=emp_no).first()
        if not emp:
            missing_set.add(emp_no)
        return emp

    def _check_employees(self, apportions, missing_set):
        for ap in apportions:
            self._get_employee(ap['employee_number'], missing_set)

    def _print_plan(self, idx, no, company, service_label, service_fee, advance, ar_total,
                    apportions, missing_set):
        self.stdout.write(f"\n  [列{idx}] {no}  {company}")
        self.stdout.write(f"      借 1123 應收帳款  {ar_total:>10,}")
        code = {'1': '400001 簽證收入', '2': '400002 記帳收入', '3': '400003 登記收入'}[service_label[0]]
        self.stdout.write(f"        貸 {code}  {service_fee:>10,}")
        if advance > 0:
            self.stdout.write(f"        貸 2192 股東往來    {advance:>10,}")
        for ap in apportions:
            emp = self._get_employee(ap['employee_number'], missing_set)
            tag = f"編號 {ap['employee_number']}" if ap['employee_number'] else self.style.ERROR('未對應姓名')
            found = '✓' if emp else '(本機無此員工)'
            self.stdout.write(f"        分攤 {ap['name']} {ap['ratio']}% ${ap['amount']:,} → {tag} {found}")

    def _print_summary(self, dry_run, created, skipped, errors, voucher_count, apportion_count,
                       sum_ar, sum_service, sum_advance, unmapped_names, missing_employees,
                       mismatch_rows, partial_rows):
        self.stdout.write(self.style.WARNING("\n=== 統計 ==="))
        verb = '預計建立' if dry_run else '已建立'
        self.stdout.write(f"  {verb}應收：{created}　跳過(已存在)：{skipped}　失敗：{errors}")
        if not dry_run:
            self.stdout.write(f"  產生傳票：{voucher_count}　公費分攤：{apportion_count}")
        self.stdout.write(f"  應收總額合計：{sum_ar:,}（服務費 {sum_service:,} + 代墊 {sum_advance:,}）")

        if mismatch_rows:
            self.stdout.write(self.style.ERROR(f"\n  ⚠ 服務費+代墊 ≠ 應收總額（{len(mismatch_rows)} 筆）："))
            for no, got, expect in mismatch_rows[:20]:
                self.stdout.write(f"     {no}: 明細 {got:,} vs 應收 {expect:,}")

        if partial_rows:
            self.stdout.write(self.style.ERROR(f"\n  ⚠ 未收 ≠ 應收（疑似已部分收款，{len(partial_rows)} 筆）："))
            for no, unpaid, ar in partial_rows[:20]:
                self.stdout.write(f"     {no}: 未收 {unpaid:,} vs 應收 {ar:,}")

        if unmapped_names:
            self.stdout.write(self.style.ERROR(f"\n  ⚠ 姓名不在對照表（{len(unmapped_names)}）：{'、'.join(sorted(unmapped_names))}"))

        if missing_employees:
            self.stdout.write(self.style.WARNING(
                f"\n  ⚠ DB 找不到員工編號（{len(missing_employees)}）：{'、'.join(sorted(missing_employees))}"
                + ("（本機無員工資料屬正常，Railway 上應可對應）" if dry_run else "（該分攤已建立但 employee=None，請手動補）")
            ))

        self.stdout.write(self.style.SUCCESS("\n完成。" + ("（未寫入任何資料）" if dry_run else "")))
