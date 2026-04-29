from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from .models.receivable import Receivable
from modules.internal_accounting.models.voucher import Voucher
from modules.internal_accounting.models.voucher_detail import VoucherDetail
from modules.internal_accounting.models.account import Account

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
        Generates a Voucher and associated VoucherDetails from a ClientBill.
        Mapping rules for billing:
        - Total Service Fees (items not starting with 8 or 9) -> Cr 400002 記帳收入
        - Total Advance Payments (items starting with 9) -> Cr 613202 發票及郵資
        - Uncollected Total (Balance) -> Dr 1123 應收帳款
        """
        if not bill.quotation_data:
            raise ValueError("無帳單明細資料，無法產生傳票")

        company_vat = bill.client.tax_id or ''

        # Required accounts
        account_mapping = {
            '400002': '記帳收入',
            '613202': '發票及郵資',
            '1123': '應收帳款',
        }
        
        accounts = {code: Account.objects.filter(code=code).first() for code in account_mapping.keys()}
        missing_accounts = [code for code, acc in accounts.items() if not acc]
        if missing_accounts:
            raise ValueError(f"系統缺少必要的會計科目代碼：{', '.join(missing_accounts)}，請先至會計科目管理新增。")

        service_fee_total = 0
        advance_payment_total = 0
        
        # Calculate totals
        for item in bill.quotation_data:
            if not isinstance(item, dict):
                continue
                
            service_name = str(item.get('service_name', '')).strip()
            amount = float(item.get('amount', 0))

            if not service_name or amount <= 0:
                continue

            if service_name.startswith('9'):
                advance_payment_total += amount
            elif not service_name.startswith('8'):
                service_fee_total += amount

        entries = []
        
        if service_fee_total > 0:
            entries.append({'type': 'credit', 'account': accounts['400002'], 'amount': service_fee_total, 'remark': '服務費用合計'})
            
        if advance_payment_total > 0:
            entries.append({'type': 'credit', 'account': accounts['613202'], 'amount': advance_payment_total, 'remark': '代墊款合計'})
            
        uncollected_total = service_fee_total + advance_payment_total
        if uncollected_total > 0:
            entries.append({'type': 'debit', 'account': accounts['1123'], 'amount': uncollected_total, 'remark': '未收款合計'})

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
        
        bill.is_posted = True
        bill.save(update_fields=['is_posted'])
        
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
