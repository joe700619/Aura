from django.core.management.base import BaseCommand
from modules.system_config.models import MenuItem

class Command(BaseCommand):
    help = 'Initialize Shareholder Services menu items'

    def handle(self, *args, **options):
        # 1. Find the parent menu item "Registration" (assuming it exists, otherwise create it or attach to root)
        # Based on previous context, there is a "Registration" module. Let's find its menu item.
        # We'll search by title or url_name. Let's assume there is a parent item.
        # If not sure, we can list existing items. But for now, let's try to find "工商登記" or similar.
        
        parent_title = "工商登記"
        parent = MenuItem.objects.filter(title=parent_title).first()
        
        if not parent:
            self.stdout.write(self.style.WARNING(f'Parent menu "{parent_title}" not found. Creating it...'))
            parent = MenuItem.objects.create(
                title=parent_title,
                # icon_svg='',  # specific icon
                order=20,  # adjust order as needed
                is_active=True
            )
        
        # 2. Create "Shareholder Services" (股務作業) as a child of Registration
        # Actually, the user requirement says "1. registration之下建立股務作業".
        # So "Shareholder Services" should be a submenu under "Registration".
        
        shareholder_services_title = "股務作業"
        shareholder_services = MenuItem.objects.filter(title=shareholder_services_title, parent=parent).first()
        
        if not shareholder_services:
            shareholder_services = MenuItem.objects.create(
                parent=parent,
                title=shareholder_services_title,
                # icon_svg='', # appropriate icon
                order=10, # first item under this section?
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created menu item "{shareholder_services_title}"'))
        else:
            self.stdout.write(f'Menu item "{shareholder_services_title}" already exists')

        # 3. Create "Shareholder List" (股東及董監事名單) under "Shareholder Services"
        shareholder_list_title = "股東及董監事名單"
        shareholder_list_url = "registration:shareholder_list"
        
        shareholder_list = MenuItem.objects.filter(title=shareholder_list_title, parent=shareholder_services).first()
        
        if not shareholder_list:
            MenuItem.objects.create(
                parent=shareholder_services,
                title=shareholder_list_title,
                url_name=shareholder_list_url,
                order=10,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created menu item "{shareholder_list_title}"'))
        else:
            # Update URL just in case
            if shareholder_list.url_name != shareholder_list_url:
                shareholder_list.url_name = shareholder_list_url
                shareholder_list.save()
                self.stdout.write(self.style.SUCCESS(f'Updated URL for "{shareholder_list_title}"'))
            else:
                self.stdout.write(f'Menu item "{shareholder_list_title}" already exists')

        # 4. Create "Equity Transaction" (股權交易) under "Shareholder Services"
        equity_transaction_title = "股權交易"
        equity_transaction_url = "registration:equity_transaction_list"
        
        equity_transaction = MenuItem.objects.filter(title=equity_transaction_title, parent=shareholder_services).first()
        
        if not equity_transaction:
            MenuItem.objects.create(
                parent=shareholder_services,
                title=equity_transaction_title,
                url_name=equity_transaction_url,
                order=20,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created menu item "{equity_transaction_title}"'))
        else:
             # Update URL just in case
            if equity_transaction.url_name != equity_transaction_url:
                equity_transaction.url_name = equity_transaction_url
                equity_transaction.save()
                self.stdout.write(self.style.SUCCESS(f'Updated URL for "{equity_transaction_title}"'))
            else:
                self.stdout.write(f'Menu item "{equity_transaction_title}" already exists')
