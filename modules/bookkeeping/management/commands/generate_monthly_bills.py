"""
自動產生記帳客戶月帳單

Usage:
    python manage.py generate_monthly_bills           # 產生當月帳單
    python manage.py generate_monthly_bills --year 2026 --month 3  # 指定年月
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from modules.bookkeeping.models import BookkeepingClient
from modules.bookkeeping.models.billing import ServiceFee, ClientBill, ClientBillItem


class Command(BaseCommand):
    help = '依服務費用定義自動產生記帳客戶月帳單'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='指定年度 (預設為當年)')
        parser.add_argument('--month', type=int, help='指定月份 (預設為當月)')

    def handle(self, *args, **options):
        today = timezone.now().date()
        year = options.get('year') or today.year
        month = options.get('month') or today.month

        self.stdout.write(f'開始產生 {year}/{month:02d} 月帳單...')

        # 只針對收費中的客戶
        clients = BookkeepingClient.objects.filter(
            is_deleted=False,
            billing_status=BookkeepingClient.BillingStatus.BILLING,
        )

        created_count = 0
        skipped_count = 0

        for client in clients:
            # 查找該客戶目前有效的 ServiceFee
            active_fees = ServiceFee.objects.filter(
                client=client,
                is_deleted=False,
                effective_date__lte=today,
            ).filter(
                # end_date 為空 或 end_date >= 今天
                **{'end_date__isnull': True}
            ) | ServiceFee.objects.filter(
                client=client,
                is_deleted=False,
                effective_date__lte=today,
                end_date__gte=today,
            )

            # 篩選收費月份包含當月的 (目前定義為固定填寫月份或 13 表示每月/依照週期)
            # 因為現在變成單一數字，我們需要依照 billing_cycle 和 billing_months 來判斷
            fees_for_month = []
            for fee in active_fees:
                # 簡單邏輯：若是月繳，或是當前月份等於設定的收費月份，或者是透過收費週期判斷
                # 如果使用者是要直接用 billing_months 紀錄 13
                # 這裡我們先簡化：如果是月繳，或者當月符合，就產生
                if fee.billing_cycle == ServiceFee.BillingCycle.MONTHLY:
                    fees_for_month.append(fee)
                elif fee.billing_months == month:
                    fees_for_month.append(fee)
                # 您可以依據之後的需求進一步完善此處的判斷邏輯

            if not fees_for_month:
                continue

            # 避免重複：已有相同 client+year+month 就跳過
            if ClientBill.objects.filter(
                client=client, year=year, month=month, is_deleted=False
            ).exists():
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  跳過 {client.name}：已有 {year}/{month:02d} 帳單')
                )
                continue

            # 產生帳單
            with transaction.atomic():
                bill = ClientBill.objects.create(
                    client=client,
                    year=year,
                    month=month,
                    bill_date=today,
                    status=ClientBill.BillStatus.DRAFT,
                )

                for fee in fees_for_month:
                    # 服務費用
                    if fee.service_fee and fee.service_fee > 0:
                        ClientBillItem.objects.create(
                            bill=bill,
                            service_fee_ref=fee,
                            description=f'服務費用 ({fee.get_billing_cycle_display()})',
                            amount=fee.service_fee,
                        )
                    # 帳簿費用
                    if fee.ledger_fee and fee.ledger_fee > 0:
                        ClientBillItem.objects.create(
                            bill=bill,
                            service_fee_ref=fee,
                            description=f'帳簿費用 ({fee.get_billing_cycle_display()})',
                            amount=fee.ledger_fee,
                        )

                bill.recalculate_total()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {client.name}：{bill.bill_no} (NT$ {bill.total_amount})')
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n完成！產生 {created_count} 張帳單，跳過 {skipped_count} 張 (已存在)'
        ))
