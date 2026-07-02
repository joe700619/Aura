"""
一次性匯入 Ragic O090 代墊款明細 → Aura 代墊款模組。

用途：把 Ragic 尚未向客戶請款的代墊款帶入 Aura（xlsx 直讀，約 150 張單 / 287 筆明細）。
- 以「代墊款序號」（OOP-YYYYMMDD-NNN）分組：一組 = 一張 AdvancePayment + 多筆明細。
- 代墊付款皆發生於 Aura 建帳之前 → is_posted=True，不產傳票（銀行/費用已含在期初，補傳票會重複）。
- 全部未向客戶請款 → 明細 is_billed=False、is_customer_absorbed=True，之後走正常發單。
  （檔案的「是否已發單」✓ 是 Ragic 端「需發單」註記，非 Aura 的已發單。）
- 核准流程不走：直接建 status=APPROVED 的 ApprovalRequest，避免產生待審單。
- 客戶用統編對 basic_data.Customer；對不到的仍建明細（customer=None、留統編）並列清單。

冪等：已存在的 advance_no 直接跳過，可重複執行。

用法：
    python manage.py import_advance_payments_from_ragic <xlsx路徑> --dry-run     # 試跑，不寫入
    python manage.py import_advance_payments_from_ragic <xlsx路徑> --user <帳號> # 正式匯入（Railway）
"""
from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from modules.administrative.models import AdvancePayment, AdvancePaymentDetail

WORKFLOW_CODE = 'advance_payment_approval'

EXPECTED_HEADER = ['代墊款序號', '統一編號', '費用歸屬', '日期', '代墊類型', '事由',
                   '代墊費用', '記帳收據編號', '是否已發單', '序號']

# Ragic 代墊類型 → AdvancePaymentDetail.PaymentType；「其他」無對應 → None
PAYMENT_TYPE_MAP = {
    '郵資': 'POSTAGE',
    '統購發票': 'GROUP_INVOICE',
    '稅款': 'TAX',
    '補充保費': 'SUPPLEMENTARY_PREMIUM',
    '政府規費': 'GOV_FEE',
    '零買發票': 'RETAIL_INVOICE',
    '印章': 'SEAL',
}


class Command(BaseCommand):
    help = '一次性匯入 Ragic O090 代墊款明細（不產傳票、不走核准流程）'

    def add_arguments(self, parser):
        parser.add_argument('xlsx_path', type=str, help='xlsx 檔路徑')
        parser.add_argument('--dry-run', action='store_true', help='只驗證與統計，不寫入資料庫')
        parser.add_argument('--user', type=str, help='申請人/核准請求人帳號（預設取第一個 superuser）')
        parser.add_argument('--limit', type=int, help='只處理前 N 張單（測試用）')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        groups = self._read_groups(options['xlsx_path'])
        if options.get('limit'):
            groups = OrderedDict(list(groups.items())[:options['limit']])

        user = self._resolve_user(options.get('user'))
        workflow_template = self._resolve_workflow()

        mode = 'DRY-RUN（不寫入）' if dry_run else '正式匯入'
        detail_total = sum(len(v) for v in groups.values())
        self.stdout.write(self.style.WARNING(f"=== {mode}｜{len(groups)} 張單 / {detail_total} 筆明細 ==="))

        created = skipped = errors = detail_count = 0
        sum_amount = 0
        unmatched_customers = {}   # 統編 → 費用歸屬名稱（DB 對不到）
        unknown_types = {}         # 未對應代墊類型 → 筆數

        from modules.basic_data.models import Customer

        for no, rows in groups.items():
            date = rows[0]['date']
            total = sum(r['amount'] for r in rows)
            sum_amount += total

            for r in rows:
                if r['type_raw'] and r['type_raw'] not in PAYMENT_TYPE_MAP:
                    unknown_types[r['type_raw']] = unknown_types.get(r['type_raw'], 0) + 1

            # 既有 → 跳過（冪等）
            if AdvancePayment.objects.filter(advance_no=no).exists():
                skipped += 1
                continue

            # 先解析客戶（dry-run 也要統計對不到的）
            for r in rows:
                r['customer'] = Customer.objects.filter(tax_id=r['tax_id']).first()
                if not r['customer']:
                    unmatched_customers[r['tax_id']] = r['company']

            if dry_run:
                created += 1
                detail_count += len(rows)
                if created <= 5:
                    self._print_plan(no, date, total, rows)
                continue

            # ── 正式寫入（每張單獨立 transaction）──
            try:
                with transaction.atomic():
                    ap = AdvancePayment.objects.create(
                        advance_no=no,
                        date=date,
                        applicant=user,
                        total_amount=total,
                        note='Ragic O090 代墊款明細匯入',
                        is_posted=True,  # 付款發生於建帳前，不再拋轉傳票
                    )
                    for r in rows:
                        AdvancePaymentDetail.objects.create(
                            advance_payment=ap,
                            is_customer_absorbed=True,
                            customer=r['customer'],
                            unified_business_no=r['tax_id'],
                            reason=r['reason'],
                            amount=r['amount'],
                            is_billed=False,
                            payment_type=PAYMENT_TYPE_MAP.get(r['type_raw']),
                        )
                    # 直接建已核准的請求（不走 services 送審，避免對核准者發通知）
                    from modules.workflow.models import ApprovalRequest
                    now = timezone.now()
                    ApprovalRequest.objects.create(
                        content_type=ContentType.objects.get_for_model(AdvancePayment),
                        object_id=ap.pk,
                        workflow_template=workflow_template,
                        status='APPROVED',
                        requester=user,
                        submit_date=now,
                        completed_date=now,
                    )
                created += 1
                detail_count += len(rows)
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  {no} 匯入失敗：{e}"))

        self._print_summary(dry_run, created, skipped, errors, detail_count,
                            sum_amount, unmatched_customers, unknown_types)

    # ───────────────────────── helpers ─────────────────────────
    def _read_groups(self, path):
        """讀 xlsx，依代墊款序號分組。回傳 OrderedDict[no] = [row dict, ...]"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except FileNotFoundError:
            raise CommandError(f"找不到檔案：{path}")

        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        header = [str(c or '').strip() for c in rows[0]]
        if header[:len(EXPECTED_HEADER)] != EXPECTED_HEADER:
            raise CommandError(f"表頭不符，預期 {EXPECTED_HEADER}，實際 {header}")

        groups = OrderedDict()
        for i, row in enumerate(rows[1:], start=2):
            if not row or not str(row[0] or '').strip():
                continue
            no = str(row[0]).strip()
            date = row[3].date() if hasattr(row[3], 'date') else row[3]
            if not date:
                raise CommandError(f"[列{i}] {no} 缺日期")
            amount = int(row[6] or 0)
            if amount <= 0:
                self.stdout.write(self.style.WARNING(f"  ⚠ [列{i}] {no} 金額為 {row[6]!r}，該列跳過"))
                continue
            item = {
                'date': date,
                'tax_id': str(row[1] or '').strip(),
                'company': str(row[2] or '').strip(),
                'type_raw': str(row[4] or '').strip(),
                'reason': str(row[5] or '').strip()[:255],
                'amount': amount,
            }
            groups.setdefault(no, [])
            # 同單日期應一致（來源已驗證）；不一致直接擋下避免 silent 歸錯日期
            if groups[no] and groups[no][0]['date'] != date:
                raise CommandError(f"[列{i}] {no} 單內日期不一致：{groups[no][0]['date']} vs {date}")
            groups[no].append(item)

        self.stdout.write(f"讀檔成功（{len(groups)} 張單）")
        return groups

    def _resolve_user(self, username):
        User = get_user_model()
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                raise CommandError(f"找不到帳號：{username}")
            return user
        user = User.objects.filter(is_superuser=True).order_by('id').first()
        if not user:
            raise CommandError("找不到 superuser，請用 --user 指定申請人")
        return user

    def _resolve_workflow(self):
        from modules.workflow.models import WorkflowTemplate
        template = WorkflowTemplate.objects.filter(code=WORKFLOW_CODE).first()
        if not template:
            raise CommandError(f"找不到工作流程 {WORKFLOW_CODE}，請先建立（核准狀態需掛在該流程下）")
        return template

    def _print_plan(self, no, date, total, rows):
        self.stdout.write(f"\n  {no}（{date}）合計 {total:,}")
        for r in rows:
            ptype = PAYMENT_TYPE_MAP.get(r['type_raw']) or self.style.WARNING(f"無對應({r['type_raw']})")
            cust = '✓' if r['customer'] else self.style.ERROR('客戶未對應')
            self.stdout.write(f"      {r['tax_id']} {r['company']} {cust}｜{r['type_raw']}→{ptype}｜{r['amount']:,}｜{r['reason']}")

    def _print_summary(self, dry_run, created, skipped, errors, detail_count,
                       sum_amount, unmatched_customers, unknown_types):
        self.stdout.write(self.style.WARNING("\n=== 統計 ==="))
        verb = '預計建立' if dry_run else '已建立'
        self.stdout.write(f"  {verb}代墊款單：{created}（明細 {detail_count} 筆）　跳過(已存在)：{skipped}　失敗：{errors}")
        self.stdout.write(f"  代墊費用合計：{sum_amount:,}")

        if unknown_types:
            pairs = '、'.join(f"{t}×{n}" for t, n in unknown_types.items())
            self.stdout.write(self.style.WARNING(f"\n  ⚠ 代墊類型無對應（payment_type 留空）：{pairs}"))

        if unmatched_customers:
            self.stdout.write(self.style.ERROR(f"\n  ⚠ 統編對不到客戶（{len(unmatched_customers)} 個，明細仍建立、customer 留空）："))
            for tax_id, name in sorted(unmatched_customers.items()):
                self.stdout.write(f"     {tax_id} {name}")

        self.stdout.write(self.style.SUCCESS("\n完成。" + ("（未寫入任何資料）" if dry_run else "")))
