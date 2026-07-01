from django.core.management.base import BaseCommand
from django.db import transaction

from modules.internal_accounting.models import Voucher


class Command(BaseCommand):
    help = '一次性：把所有草稿(DRAFT)傳票整批改為已過帳(POSTED)。排除軟刪除。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會影響幾筆，不實際寫入。',
        )

    def handle(self, *args, **options):
        qs = Voucher.objects.filter(
            status=Voucher.Status.DRAFT,
            is_deleted=False,
        )
        count = qs.count()

        if count == 0:
            self.stdout.write(self.style.WARNING('沒有草稿傳票需要過帳。'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE(f'[dry-run] 將有 {count} 筆草稿傳票會被改為「已過帳」，未寫入。'))
            return

        # 整批更新。此為一次性資料處理，不逐筆 save()（不觸發 simple_history 紀錄），
        # 換取效能與簡潔；狀態變更沒有 signal 副作用。
        with transaction.atomic():
            updated = qs.update(status=Voucher.Status.POSTED)

        self.stdout.write(self.style.SUCCESS(f'已將 {updated} 筆草稿傳票改為「已過帳」。'))
