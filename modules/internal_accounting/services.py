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
        today = timezone.now().date()
        today_str = today.strftime('%Y%m%d')
        count = Voucher.objects.filter(date=today).count() + 1
        voucher_no = f'VOU-{today_str}-{count:03d}'

        voucher = Voucher.objects.create(
            date=today,
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
