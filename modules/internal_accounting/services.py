from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from .models.receivable import Receivable
from modules.internal_accounting.models.voucher import Voucher
from modules.internal_accounting.models.voucher_detail import VoucherDetail
from modules.internal_accounting.models.account import Account

# 帳單拋轉傳票會用到的科目（服務費、各代墊款科目、應收帳款），供前端預覽取多視角設定
BILLING_VOUCHER_ACCOUNT_CODES = ['400002', '613202', '613203', '1141', '1142', '613204', '6132', '1123']


def get_account_aux_types(codes):
    """回傳指定科目代碼 → auxiliary_type 對照，供前端預覽判斷是否帶統編到往來對象。"""
    return dict(Account.objects.filter(code__in=codes).values_list('code', 'auxiliary_type'))


class ReceivableTransferService:
    @staticmethod
    @transaction.atomic
    def create_from_source(source_obj):
        """
        Creates a Receivable record from a source object.
        The source object must implement a to_ar_data() method.
        """
        if not hasattr(source_obj, 'to_ar_data'):
            raise ValueError(f"Source object {source_obj} does not implement to_ar_data()")

        data = source_obj.to_ar_data()
        
        # Generate AR number
        today_str = timezone.now().strftime('%Y%m%d')
        prefix = f"RO{today_str}"
        last_obj = Receivable.objects.filter(receivable_no__startswith=prefix).order_by('-receivable_no').first()
        if last_obj:
            try:
                last_seq = int(last_obj.receivable_no[-3:])
                new_seq = last_seq + 1
            except (ValueError, TypeError):
                new_seq = 1
        else:
            new_seq = 1
        receivable_no = f"{prefix}{new_seq:03d}"

        # 1. Create the Receivable record
        receivable = Receivable.objects.create(
            receivable_no=receivable_no,
            date=data.get('date'),
            assistant=data.get('assistant'),
            company_name=data.get('company_name'),
            unified_business_no=data.get('unified_business_no'),
            main_contact=data.get('main_contact'),
            mobile=data.get('mobile'),
            phone=data.get('phone'),
            address=data.get('address'),
            line_id=data.get('line_id'),
            room_id=data.get('room_id'),
            quotation_data=data.get('quotation_data', []),
            cost_sharing_data=data.get('cost_sharing_data', []),
            remarks=data.get('remarks', ''),
            
            # Record the source for traceability
            source_content_type=ContentType.objects.get_for_model(source_obj),
            source_id=source_obj.pk
        )

        cost_sharing_data = data.get('cost_sharing_data', [])
        if cost_sharing_data:
            from modules.internal_accounting.models.receivable import ReceivableFeeApportion
            import json
            
            if isinstance(cost_sharing_data, str):
                try:
                    parsed_cost_sharing = json.loads(cost_sharing_data)
                except Exception:
                    parsed_cost_sharing = []
            else:
                parsed_cost_sharing = cost_sharing_data
                
            for item in parsed_cost_sharing:
                if not isinstance(item, dict):
                    continue
                employee_id = item.get('employee_id')
                if employee_id:
                    ReceivableFeeApportion.objects.create(
                        receivable=receivable,
                        employee_id=employee_id,
                        task_description=item.get('task_description', '')[:255] if item.get('task_description') else '',
                        ratio=item.get('ratio') or 0,
                        amount=item.get('amount') or 0
                    )
        
        # 2. Mark the source as transferred if it has the field
        if hasattr(source_obj, 'is_ar_transferred'):
            source_obj.is_ar_transferred = True
            source_obj.save(update_fields=['is_ar_transferred'])
            
        return receivable

    @staticmethod
    @transaction.atomic
    def generate_voucher_for_progress(progress, user):
        """
        Generates a Voucher and associated VoucherDetails from a Progress record.
        Mapping quotation prefixes to specific accounting codes as per standard mapping rules.
        """
        if not progress.quotation_data:
            raise ValueError("無報價單資料，無法產生傳票")

        company_vat = progress.unified_business_no or ''

        account_mapping = {
            '400001': '簽證收入',
            '400002': '記帳收入',
            '400003': '登記收入',
            '1140': '預付款項',
            '2190': '預收款項',
            '1123': '應收帳款',
        }
        
        # Pre-fetch required accounts
        accounts = {code: Account.objects.filter(code=code).first() for code in account_mapping.keys()}
        missing_accounts = [code for code, acc in accounts.items() if not acc]
        if missing_accounts:
            raise ValueError(f"系統缺少必要的會計科目代碼：{', '.join(missing_accounts)}，請先至會計科目管理新增。")

        entries = []
        
        for item in progress.quotation_data:
            if not isinstance(item, dict):
                continue
                
            service_name = str(item.get('service_name', '')).strip()
            amount = float(item.get('amount', 0))
            remark = str(item.get('remark', ''))

            if service_name.startswith('8'):
                amount = abs(amount)

            if not service_name or amount <= 0:
                continue

            if service_name.startswith('1'):
                if amount > 0:
                    entries.append({'type': 'credit', 'account': accounts['400001'], 'amount': amount, 'remark': remark})
            elif service_name.startswith('2'):
                if amount > 0:
                    entries.append({'type': 'credit', 'account': accounts['400002'], 'amount': amount, 'remark': remark})
            elif service_name.startswith('3'):
                if amount > 0:
                    entries.append({'type': 'credit', 'account': accounts['400003'], 'amount': amount, 'remark': remark})
            elif service_name.startswith('9'):
                if amount > 0:
                    entries.append({'type': 'credit', 'account': accounts['1140'], 'amount': amount, 'remark': remark})
            elif service_name.startswith('8'):
                if amount > 0:
                    entries.append({'type': 'debit', 'account': accounts['2190'], 'amount': amount, 'remark': remark})
        
        # Calculate Uncollected Total
        total_credits = sum(e['amount'] for e in entries if e['type'] == 'credit')
        total_debits = sum(e['amount'] for e in entries if e['type'] == 'debit')
        
        balance_diff = total_credits - total_debits
        if balance_diff > 0:
            # Debit Accounts Receivable
            entries.append({'type': 'debit', 'account': accounts['1123'], 'amount': balance_diff, 'remark': '未收款合計'})
        elif balance_diff < 0:
            # Credit Accounts Receivable (Overpaid)
            entries.append({'type': 'credit', 'account': accounts['1123'], 'amount': abs(balance_diff), 'remark': '未收款合計 (溢收)'})

        if not entries:
            return None

        # Create the Voucher
        today = timezone.now().date()
        today_str = today.strftime('%Y%m%d')
        count = Voucher.objects.filter(date=today).count() + 1
        voucher_no = f'VOU-{today_str}-{count:03d}'

        voucher = Voucher.objects.create(
            date=today,
            voucher_no=voucher_no,
            description=f"登記案件過帳: {progress.company_name}",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.SYSTEM,
            created_by=user
        )

        for entry in entries:
            company_id = ''
            if entry['account'].auxiliary_type == 'PARTNER':
                company_id = company_vat

            VoucherDetail.objects.create(
                voucher=voucher,
                account=entry['account'],
                debit=entry['amount'] if entry['type'] == 'debit' else 0,
                credit=entry['amount'] if entry['type'] == 'credit' else 0,
                company_id=company_id,
                remark=entry['remark']
            )
        
        progress.is_posted = True
        progress.save(update_fields=['is_posted'])
        
        return voucher

    @staticmethod
    @transaction.atomic
    def generate_voucher_for_bill(bill, user):
        """
        依帳單產生傳票，分錄規則與前端預覽 (generateBillingEntries) 完全一致：
        - 服務費（報價單中非 8、非 9 開頭項目）合計 → 貸 400002 記帳收入
        - 代墊款（帳單附的代墊明細 advance_payment_data）依代墊類型分到各科目 → 貸
        - 未收款合計（服務費 + 代墊款）→ 借 1123 應收帳款
        - 統編只有「科目多視角＝PARTNER」才帶入往來對象 (company_id)
        """
        import json

        quotation = bill.quotation_data or []
        if isinstance(quotation, str):
            quotation = json.loads(quotation or '[]')
        advance_data = bill.advance_payment_data or []
        if isinstance(advance_data, str):
            advance_data = json.loads(advance_data or '[]')

        if not quotation and not advance_data:
            raise ValueError("無帳單明細資料，無法產生傳票")

        company_vat = bill.client.tax_id or ''

        # 代墊類型（顯示字串）→ 科目，與前端 advanceTypeMap 一致
        advance_type_map = {
            '郵資及快遞': ('613202', '郵資及快遞'),
            '統購發票':   ('613203', '發票費用'),
            '零買發票':   ('613203', '發票費用'),
            '稅款':       ('1141',   '代墊稅款及保費'),
            '補充保費':   ('1141',   '代墊稅款及保費'),
            '政府規費':   ('1142',   '代墊政府規費'),
            '印章':       ('613204', '印章費用'),
        }
        default_advance = ('6132', '代墊費用')

        # 1) 服務費合計（排除 8、9 開頭，與前端一致）
        service_fee_total = 0
        for item in quotation:
            if not isinstance(item, dict):
                continue
            service_name = str(item.get('service_name', '')).strip()
            amount = float(item.get('amount', 0) or 0)
            if amount <= 0 or service_name.startswith('8') or service_name.startswith('9'):
                continue
            service_fee_total += amount

        # 2) 代墊款依類型分組加總（來源為 advance_payment_data，與前端一致）
        advance_by_code = {}  # code -> {'name', 'total'}
        advance_total = 0
        for item in advance_data:
            if not isinstance(item, dict):
                continue
            amount = float(item.get('amount', 0) or 0)
            if amount <= 0:
                continue
            pay_type = str(item.get('payment_type', '')).strip()
            code, name = advance_type_map.get(pay_type, default_advance)
            bucket = advance_by_code.setdefault(code, {'name': name, 'total': 0})
            bucket['total'] += amount
            advance_total += amount

        uncollected_total = service_fee_total + advance_total

        # 收集需要的科目並一次檢查是否存在
        needed_codes = set(advance_by_code.keys())
        if service_fee_total > 0:
            needed_codes.add('400002')
        if uncollected_total > 0:
            needed_codes.add('1123')
        if not needed_codes:
            return None

        accounts = {code: Account.objects.filter(code=code).first() for code in needed_codes}
        missing_accounts = [code for code, acc in accounts.items() if not acc]
        if missing_accounts:
            raise ValueError(f"系統缺少必要的會計科目代碼：{', '.join(sorted(missing_accounts))}，請先至會計科目管理新增。")

        # 組分錄（順序與前端一致：服務費 → 各代墊款 → 應收帳款）
        entries = []
        if service_fee_total > 0:
            entries.append({'type': 'credit', 'account': accounts['400002'], 'amount': int(service_fee_total), 'remark': '服務費用合計'})
        for code, info in advance_by_code.items():
            entries.append({'type': 'credit', 'account': accounts[code], 'amount': int(info['total']), 'remark': '代墊款合計'})
        if uncollected_total > 0:
            entries.append({'type': 'debit', 'account': accounts['1123'], 'amount': int(uncollected_total), 'remark': '未收款合計'})

        if not entries:
            return None

        # Create the Voucher
        voucher_date = bill.bill_date or timezone.now().date()
        date_str = voucher_date.strftime('%Y%m%d')
        count = Voucher.objects.filter(date=voucher_date).count() + 1
        voucher_no = f'VOU-{date_str}-{count:03d}'

        voucher = Voucher.objects.create(
            date=voucher_date,
            voucher_no=voucher_no,
            description=f"帳單過帳: {bill.client.name} ({bill.bill_no})",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.SYSTEM,
            created_by=user
        )

        for entry in entries:
            company_id = company_vat if entry['account'].auxiliary_type == 'PARTNER' else ''
            VoucherDetail.objects.create(
                voucher=voucher,
                account=entry['account'],
                debit=entry['amount'] if entry['type'] == 'debit' else 0,
                credit=entry['amount'] if entry['type'] == 'credit' else 0,
                company_id=company_id,
                remark=entry['remark']
            )

        bill.is_posted = True
        bill.save(update_fields=['is_posted'])

        return voucher

    # 收據號碼前綴 → 服務費收入科目
    RECEIVABLE_INCOME_MAP = {
        'AU': '400001',  # 簽證收入
        'BI': '400002',  # 記帳收入
        'RO': '400003',  # 登記收入
    }

    @staticmethod
    @transaction.atomic
    def generate_voucher_for_receivable(receivable, user, voucher_date=None):
        """
        為「匯入的」應收帳款產生立帳傳票草稿（raigc 期初匯入專用）。

        分錄（方案 B：代墊走股東往來，因代墊付款發生於 Aura 建帳前、未曾入帳）：
            借 1123 應收帳款  = 服務費 + 代墊款（= 應收總額）
            貸 收入科目        = 服務費合計（依 quotation_data 前綴：1→簽證 / 2→記帳 / 3→登記）
            貸 2192 股東往來   = 代墊款合計（9 開頭）

        金額來源為 receivable.quotation_data，故傳票可由應收帳款本身重現。
        觸發時機：import_receivables_from_raigc command 逐筆呼叫。
        副作用：建立一張 DRAFT 傳票與其明細；不修改應收帳款。
        """
        quotation = receivable.quotation_data or []

        prefix_account_map = {
            '1': '400001',  # 簽證收入
            '2': '400002',  # 記帳收入
            '3': '400003',  # 登記收入
            '9': '2192',    # 股東往來（代墊）
        }

        # 依科目彙總貸方金額
        credit_by_code = {}
        for item in quotation:
            if not isinstance(item, dict):
                continue
            name = str(item.get('service_name', '')).strip()
            amount = int(item.get('amount') or 0)
            if amount <= 0 or not name:
                continue
            code = prefix_account_map.get(name[:1])
            if not code:
                continue
            credit_by_code[code] = credit_by_code.get(code, 0) + amount

        total = sum(credit_by_code.values())
        if total <= 0:
            return None

        needed_codes = set(credit_by_code) | {'1123'}
        accounts = {code: Account.objects.filter(code=code).first() for code in needed_codes}
        missing = [c for c, a in accounts.items() if not a]
        if missing:
            raise ValueError(f"系統缺少必要會計科目：{', '.join(sorted(missing))}，請先至會計科目管理新增。")

        company_vat = receivable.unified_business_no or ''

        voucher_date = voucher_date or timezone.now().date()
        date_str = voucher_date.strftime('%Y%m%d')
        count = Voucher.objects.filter(date=voucher_date).count() + 1
        voucher_no = f'VOU-{date_str}-{count:03d}'

        voucher = Voucher.objects.create(
            date=voucher_date,
            voucher_no=voucher_no,
            description=f"應收帳款期初立帳（raigc 匯入）：{receivable.company_name}（{receivable.receivable_no}）",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.SYSTEM,
            created_by=user,
        )

        # 借：應收帳款
        ar_account = accounts['1123']
        VoucherDetail.objects.create(
            voucher=voucher,
            account=ar_account,
            debit=total, credit=0,
            company_id=company_vat if ar_account.auxiliary_type == 'PARTNER' else '',
            remark='未收款合計',
        )
        # 貸：各收入科目 / 股東往來
        remark_map = {'400001': '簽證服務費', '400002': '記帳服務費', '400003': '登記服務費', '2192': '代墊款（股東往來）'}
        for code, amount in credit_by_code.items():
            acc = accounts[code]
            VoucherDetail.objects.create(
                voucher=voucher,
                account=acc,
                debit=0, credit=amount,
                company_id=company_vat if acc.auxiliary_type == 'PARTNER' else '',
                remark=remark_map.get(code, ''),
            )

        return voucher


class PreCollectionService:
    @staticmethod
    @transaction.atomic
    def post_voucher(pre_collection, user, debit_code=None, debit_name=None):
        """
        預收款項過帳：建立傳票（借：收款方式科目；貸：2190 預收款項），並標記為已核銷。
        不需要選擇應收帳款，直接產生傳票草稿。
        """
        from .models.pre_collection import PreCollection

        if pre_collection.status == PreCollection.Status.MATCHED:
            raise ValueError("此預收款項已核銷，不可重複操作。")

        method_map = {
            'ecpay': ('111403', '綠界'),
            'bank':  ('111401', '國泰世華'),
            'cash':  ('1110',   '現金'),
        }

        if pre_collection.method == 'other':
            if not debit_code:
                raise ValueError("收款方式為「其他」時，請提供借方科目代碼。")
            m_code = debit_code.strip()
            m_name = (debit_name or m_code).strip()
        else:
            m_code, m_name = method_map.get(pre_collection.method, ('111401', '銀行存款'))

        debit_account  = Account.objects.filter(code=m_code).first()
        credit_account = Account.objects.filter(code='2190').first()

        if not debit_account:
            raise ValueError(f"找不到科目 {m_code}，請先至會計科目管理新增。")
        if not credit_account:
            raise ValueError("找不到科目 2190 預收款項，請先至會計科目管理新增。")

        amount = int(pre_collection.amount)
        company_vat = pre_collection.unified_business_no or ''

        # 建立傳票
        voucher_date = pre_collection.date
        date_str = voucher_date.strftime('%Y%m%d')
        count = Voucher.objects.filter(date=voucher_date).count() + 1
        voucher_no = f'VOU-{date_str}-{count:03d}'

        voucher = Voucher.objects.create(
            date=voucher_date,
            voucher_no=voucher_no,
            description=f"預收款項過帳：{pre_collection.company_name}（{pre_collection.pre_collection_no}）",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.COLLECTION,
            created_by=user,
        )

        VoucherDetail.objects.create(
            voucher=voucher,
            account=debit_account,
            debit=amount, credit=0,
            company_id=company_vat if debit_account.auxiliary_type == 'PARTNER' else '',
            remark=f'收款 - {m_name}',
        )
        VoucherDetail.objects.create(
            voucher=voucher,
            account=credit_account,
            debit=0, credit=amount,
            company_id=company_vat if credit_account.auxiliary_type == 'PARTNER' else '',
            remark='預收款項',
        )

        # 標記已核銷
        pre_collection.status = PreCollection.Status.MATCHED
        pre_collection.save(update_fields=['status'])

        return voucher

    @staticmethod
    @transaction.atomic
    def match_to_billing(pre_collection, receivable, user):
        """
        記帳帳單核銷：以預收款建立收款單 → 自動過帳 → 標記核銷。
        傳票：借：綠界/銀行；貸：1123 應收帳款。
        """
        from .models.pre_collection import PreCollection
        from .models.collection import Collection

        if pre_collection.status == PreCollection.Status.MATCHED:
            raise ValueError("此預收款項已核銷，不可重複操作。")

        collection = Collection.objects.create(
            receivable=receivable,
            date=pre_collection.date,
            method=pre_collection.method,
            amount=pre_collection.amount,
            tax=0,
            fee=0,
            allowance=0,
            remarks=f"預收款核銷 {pre_collection.pre_collection_no}",
            auto_created=False,
        )

        AccountingService.post_collection(collection, user)

        pre_collection.status = PreCollection.Status.MATCHED
        pre_collection.matched_receivable = receivable
        pre_collection.matched_collection = collection
        pre_collection.save(update_fields=['status', 'matched_receivable', 'matched_collection'])

        return collection


class AccountingService:
    @staticmethod
    @transaction.atomic
    def post_collection(collection, user):
        """
        為單筆收款產生傳票並標記為已過帳。
        傳票日期 = 收款日期。
        借：銀行/現金/稅/費/折讓；貸：1123 應收帳款。
        """
        from .models.voucher import Voucher
        from .models.voucher_detail import VoucherDetail
        from .models.account import Account

        if collection.is_posted:
            raise ValueError("此筆收款已過帳，不可重複過帳。")

        # 檢查收款日期所屬期間是否已關帳
        from .models.period import AccountingPeriod
        period = AccountingPeriod.objects.filter(
            year=collection.date.year,
            month=collection.date.month
        ).first()
        if period and period.status == AccountingPeriod.Status.CLOSED:
            raise ValueError(
                f"{collection.date.year} 年 {collection.date.month:02d} 月已關帳，"
                f"無法對該期間的收款進行過帳。請先重新開帳後再操作。"
            )

        company_vat = collection.receivable.unified_business_no or ''

        method_map = {
            'bank':  ('111401', '國泰世華'),
            'ecpay': ('111403', '綠界'),
            'cash':  ('1110',   '現金'),
            'notes': ('1124',   '應收票據'),
        }
        method_code, method_name = method_map.get(collection.method, ('111401', '銀行存款'))

        needed_codes = {method_code, '1149', '613201', '6123', '1123'}
        accounts = {code: Account.objects.filter(code=code).first() for code in needed_codes}
        missing = [c for c, a in accounts.items() if not a]
        if missing:
            raise ValueError(f"系統缺少必要會計科目：{', '.join(missing)}，請先至會計科目管理新增。")

        entries = []
        if collection.amount > 0:
            entries.append({'type': 'debit', 'account': accounts[method_code], 'amount': collection.amount, 'remark': f'收款 - {method_name}'})
        if collection.tax > 0:
            entries.append({'type': 'debit', 'account': accounts['1149'], 'amount': collection.tax, 'remark': '扣繳稅款'})
        if collection.fee > 0:
            entries.append({'type': 'debit', 'account': accounts['613201'], 'amount': collection.fee, 'remark': '手續費'})
        if collection.allowance > 0:
            entries.append({'type': 'debit', 'account': accounts['6123'], 'amount': collection.allowance, 'remark': '壞帳或折讓'})

        total_debits = sum(e['amount'] for e in entries)
        if total_debits <= 0:
            raise ValueError("收款金額合計為 0，無法過帳。")

        entries.append({'type': 'credit', 'account': accounts['1123'], 'amount': total_debits, 'remark': '應收帳款沖帳'})

        voucher_date = collection.date
        date_str = voucher_date.strftime('%Y%m%d')
        count = Voucher.objects.filter(date=voucher_date).count() + 1
        voucher_no = f'VOU-{date_str}-{count:03d}'

        voucher = Voucher.objects.create(
            date=voucher_date,
            voucher_no=voucher_no,
            description=f"收款過帳：{collection.receivable.company_name}（{collection.collection_no}）",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.COLLECTION,
            created_by=user,
        )

        for entry in entries:
            company_id = company_vat if entry['account'].auxiliary_type == 'PARTNER' else ''
            VoucherDetail.objects.create(
                voucher=voucher,
                account=entry['account'],
                debit=entry['amount'] if entry['type'] == 'debit' else 0,
                credit=entry['amount'] if entry['type'] == 'credit' else 0,
                company_id=company_id,
                remark=entry['remark'],
            )

        collection.voucher = voucher
        collection.is_posted = True
        collection.save(update_fields=['voucher', 'is_posted'])

        return voucher

    @staticmethod
    @transaction.atomic
    def close_year(year, user):
        from datetime import date
        from django.db.models import Sum
        from .models.voucher import Voucher
        from .models.voucher_detail import VoucherDetail
        from .models.account import Account

        end_date = date(year, 12, 31)
        
        virtual_categories = [
            Account.Category.REVENUE, Account.Category.COST, 
            Account.Category.EXPENSE, Account.Category.NON_OP_INC,
            Account.Category.NON_OP_EXP, Account.Category.TAX
        ]
        
        details = VoucherDetail.objects.filter(
            voucher__date__year=year,
            account__category__in=virtual_categories,
            voucher__status=Voucher.Status.POSTED
        ).values('account_id', 'account__name', 'account__category').annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        # 刪除同年度舊的結轉傳票（草稿或已過帳皆刪），確保不重複
        old_closing = Voucher.objects.filter(
            date__year=year,
            source=Voucher.Source.YEAR_END_CLOSING
        )
        old_closing.delete()

        if not details:
            return None, "該年度無已過帳的虛帳戶明細資料需要結轉"

        entries = []
        net_profit = 0
        
        for d in details:
            balance = (d['total_credit'] or 0) - (d['total_debit'] or 0)
            if balance == 0:
                continue
                
            net_profit += balance
            
            if balance > 0:
                entries.append({
                    'account_id': d['account_id'],
                    'debit': balance,
                    'credit': 0,
                    'remark': '年度結清轉出'
                })
            else:
                entries.append({
                    'account_id': d['account_id'],
                    'debit': 0,
                    'credit': abs(balance),
                    'remark': '年度結清轉出'
                })
        
        if not entries:
            return None, "所有虛帳戶餘額已為零"
            
        accumulated_profit_account = Account.objects.filter(code='3100').first()
        if not accumulated_profit_account:
            raise ValueError("系統找不到累積盈虧科目 (3100)，請先至會計科目管理新增。")

        if net_profit > 0:
            entries.append({
                'account_id': accumulated_profit_account.code,
                'debit': 0,
                'credit': net_profit,
                'remark': f'{year}年度本期淨利結轉'
            })
        elif net_profit < 0:
            entries.append({
                'account_id': accumulated_profit_account.code,
                'debit': abs(net_profit),
                'credit': 0,
                'remark': f'{year}年度本期淨損結轉'
            })

        count = Voucher.objects.filter(date=end_date).count() + 1
        voucher_no = f'VOU-{end_date.strftime("%Y%m%d")}-{count:03d}'

        voucher = Voucher.objects.create(
            date=end_date,
            voucher_no=voucher_no,
            description=f"{year}年度結轉",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.YEAR_END_CLOSING,
            created_by=user
        )

        for entry in entries:
            VoucherDetail.objects.create(
                voucher=voucher,
                account_id=entry['account_id'],
                debit=entry['debit'],
                credit=entry['credit'],
                remark=entry['remark']
            )
            
        return voucher, "結轉傳票產生成功"

    @staticmethod
    @transaction.atomic
    def run_monthly_depreciation(year, month, user):
        from datetime import date
        from calendar import monthrange
        from .models.fixed_asset import FixedAsset
        from .models.voucher import Voucher
        from .models.voucher_detail import VoucherDetail
        
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        assets = FixedAsset.objects.filter(
            status=FixedAsset.Status.ACTIVE,
            purchase_date__lte=end_date
        )
        
        entries = []
        processed_count = 0
        total_depreciation = 0

        for asset in assets:
            if asset.net_value <= asset.salvage_value:
                continue
                
            if asset.useful_life_months <= 0:
                continue

            monthly_depreciation = (asset.cost - asset.salvage_value) / asset.useful_life_months
            monthly_depreciation = round(monthly_depreciation)
            
            max_depreciable = asset.net_value - asset.salvage_value
            if monthly_depreciation > max_depreciable:
                monthly_depreciation = max_depreciable
                
            if monthly_depreciation <= 0:
                continue

            if not asset.depreciation_expense_account_code or not asset.accumulated_depreciation_account_code:
                raise ValueError(f"資產 {asset.asset_no} ({asset.name}) 尚未設定折舊對應之會計科目。")
            
            entries.append({
                'asset': asset,
                'expense_code': asset.depreciation_expense_account_code,
                'accumulated_code': asset.accumulated_depreciation_account_code,
                'amount': monthly_depreciation
            })
            
            processed_count += 1
            total_depreciation += monthly_depreciation

        if not entries:
            return None, "無符合條件的固定資產需要提列折舊"

        count = Voucher.objects.filter(date=end_date).count() + 1
        voucher_no = f'VOU-{end_date.strftime("%Y%m%d")}-{count:03d}'
        
        voucher = Voucher.objects.create(
            date=end_date,
            voucher_no=voucher_no,
            description=f"{year}年{month}月 固定資產折舊提列",
            status=Voucher.Status.DRAFT,
            source=Voucher.Source.DEPRECIATION,
            created_by=user
        )

        for entry in entries:
            asset = entry['asset']
            amount = entry['amount']
            
            VoucherDetail.objects.create(
                voucher=voucher,
                account_id=entry['expense_code'],
                debit=amount,
                credit=0,
                project=asset.asset_no,
                remark=f'提列折舊 - {asset.name}'
            )
            
            VoucherDetail.objects.create(
                voucher=voucher,
                account_id=entry['accumulated_code'],
                debit=0,
                credit=amount,
                project=asset.asset_no,
                remark=f'提列折舊 - {asset.name}'
            )
            
            asset.accumulated_depreciation += amount
            asset.save(update_fields=['accumulated_depreciation'])

        return voucher, f"成功提列 {processed_count} 筆資產，總折舊額 ${total_depreciation}"
