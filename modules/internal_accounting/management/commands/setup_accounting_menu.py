from django.core.management.base import BaseCommand
from modules.system_config.models import MenuItem

class Command(BaseCommand):
    help = 'Setup accounting module menu items'

    def handle(self, *args, **options):
        # 1. Create Parent Menu: 內部會計
        parent, created = MenuItem.objects.get_or_create(
            title='內部會計',
            defaults={
                'icon_svg': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>',
                'order': 50,
            }
        )
        
        # 2. Create Sub-menus
        # Voucher Management
        MenuItem.objects.get_or_create(
            parent=parent,
            title='傳票作業',
            defaults={
                'url_name': 'internal_accounting:voucher_list',
                'order': 10,
            }
        )
        
        # Account Management
        MenuItem.objects.get_or_create(
            parent=parent,
            title='科目管理',
            defaults={
                'url_name': 'internal_accounting:account_list',
                'order': 20,
            }
        )
        
        # Receivable Management
        MenuItem.objects.get_or_create(
            parent=parent,
            title='應收帳款',
            defaults={
                'url_name': 'internal_accounting:receivable_list',
                'order': 30,
            }
        )
        
        # Payment Management
        MenuItem.objects.get_or_create(
            parent=parent,
            title='收款管理',
            defaults={
                'url_name': 'internal_accounting:collection_list',
                'order': 40,
            }
        )
        
        # Reports
        MenuItem.objects.get_or_create(
            parent=parent,
            title='日記帳',
            defaults={
                'url_name': 'internal_accounting:report_journal',
                'order': 50,
            }
        )
        
        MenuItem.objects.get_or_create(
            parent=parent,
            title='總分類帳',
            defaults={
                'url_name': 'internal_accounting:report_general_ledger',
                'order': 60,
            }
        )
        
        MenuItem.objects.get_or_create(
            parent=parent,
            title='輔助核算明細表',
            defaults={
                'url_name': 'internal_accounting:report_subsidiary_ledger',
                'order': 65,
            }
        )
        
        MenuItem.objects.get_or_create(
            parent=parent,
            title='損益表',
            defaults={
                'url_name': 'internal_accounting:report_income_statement',
                'order': 70,
            }
        )
        
        MenuItem.objects.get_or_create(
            parent=parent,
            title='資產負債表',
            defaults={
                'url_name': 'internal_accounting:report_balance_sheet',
                'order': 80,
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully setup internal accounting menu items'))
