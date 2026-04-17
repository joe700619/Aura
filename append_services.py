import os

target_path = r"C:\Users\joe70\PythonProject\Aura\modules\internal_accounting\services.py"

code_to_append = """

class AccountingService:
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
"""

with open(target_path, "a", encoding="utf-8") as f:
    f.write(code_to_append)
print("Successfully appended AccountingService to services.py")
