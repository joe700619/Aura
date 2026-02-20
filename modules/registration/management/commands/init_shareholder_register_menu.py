from django.core.management.base import BaseCommand
from modules.system_config.models import MenuItem

class Command(BaseCommand):
    help = 'Initialize Shareholder Register Query menu item'

    def handle(self, *args, **options):
        # 1. Find the parent menu item "Shareholder Services" (股務作業)
        parent_title = "股務作業"
        parent = MenuItem.objects.filter(title=parent_title).first()
        
        if not parent:
            self.stdout.write(self.style.ERROR(f'Parent menu "{parent_title}" not found. Please run init_shareholder_menu first.'))
            return

        # 2. Create "Shareholder Register Query" (股東名簿查詢) under "Shareholder Services"
        item_title = "股東名簿查詢"
        item_url = "registration:shareholder_register_list"
        
        item = MenuItem.objects.filter(title=item_title, parent=parent).first()
        
        if not item:
            MenuItem.objects.create(
                parent=parent,
                title=item_title,
                url_name=item_url,
                order=30,  # After Equity Transaction (20)
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created menu item "{item_title}"'))
        else:
            # Update URL just in case
            if item.url_name != item_url:
                item.url_name = item_url
                item.save()
                self.stdout.write(self.style.SUCCESS(f'Updated URL for "{item_title}"'))
            else:
                self.stdout.write(f'Menu item "{item_title}" already exists')
