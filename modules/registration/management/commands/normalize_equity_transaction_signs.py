from django.core.management.base import BaseCommand
from django.db import transaction

from modules.registration.models.equity_transaction import EquityTransaction


class Command(BaseCommand):
    help = (
        '依交易事由將既有股權交易的 share_count / total_amount 正規化為正/負號。'
        '減少類事由（減資、賣出、贈與、合併減少、分割減少、其他減少）存負數，其餘存正數。'
        '邏輯為 idempotent，重複執行安全。預設只顯示不寫入，加 --apply 才實際寫入。'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='實際寫入資料庫（不加此參數時為 dry-run，只顯示會變動的筆數）',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        decrease = EquityTransaction.DECREASE_REASONS

        changed = []
        for tx in EquityTransaction.objects.all().iterator():
            is_decrease = tx.transaction_reason in decrease
            if tx.share_count is None:
                continue
            magnitude = abs(tx.share_count)
            new_count = -magnitude if is_decrease else magnitude
            if new_count != tx.share_count:
                changed.append((tx.pk, tx.get_transaction_reason_display(), tx.share_count, new_count))

        if not changed:
            self.stdout.write(self.style.SUCCESS('沒有需要修正的交易，資料已經正確。'))
            return

        self.stdout.write(f'共 {len(changed)} 筆需要修正：')
        for pk, reason, old, new in changed[:50]:
            self.stdout.write(f'  #{pk}  {reason}  {old} → {new}')
        if len(changed) > 50:
            self.stdout.write(f'  ...（其餘 {len(changed) - 50} 筆略）')

        if not apply:
            self.stdout.write(self.style.WARNING('\n這是 dry-run，未寫入。確認無誤後加 --apply 正式執行。'))
            return

        # 逐筆 save()，由 model 的 save() 正規化正負號（含 total_amount 與歷史紀錄）
        ids = [pk for pk, _, _, _ in changed]
        with transaction.atomic():
            for tx in EquityTransaction.objects.filter(pk__in=ids).iterator():
                tx.save()

        self.stdout.write(self.style.SUCCESS(f'\n已修正 {len(changed)} 筆。'))
