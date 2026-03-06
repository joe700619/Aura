"""
年度假期重算 Management Command（週年制）

用法：
    python manage.py recalculate_leave              # 計算當前在職員工
    python manage.py recalculate_leave --dry-run     # 預覽，不實際寫入
"""

from django.core.management.base import BaseCommand
from modules.hr.services.leave_calculator import recalculate_leave_balances


class Command(BaseCommand):
    help = '依勞基法（週年制）重新計算員工特休及病假額度'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅預覽計算結果，不實際寫入資料庫',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== 預覽模式 (DRY RUN) ===\n'))
        else:
            self.stdout.write(self.style.SUCCESS('=== 開始計算（週年制） ===\n'))

        results = recalculate_leave_balances(dry_run=dry_run)

        for r in results:
            action_str = {
                'preview': '📋',
                'created': '✅',
                'checked': '—',
                'exists': '—',
            }.get(r['action'], '?')

            self.stdout.write(
                f"  {action_str} {r['employee']} | {r['leave_type']} | "
                f"{r['days']}天 = {r['hours']}h | {r['period']} ({r['seniority']})"
            )

        created = [r for r in results if r['action'] == 'created']
        self.stdout.write(self.style.SUCCESS(
            f'\n完成！共處理 {len(results)} 筆，新建 {len(created)} 筆。'
        ))
