from django.core.management.base import BaseCommand
from modules.system_config.models import MenuItem

class Command(BaseCommand):
    help = 'Add business tax menu item under bookkeeping'

    def handle(self, *args, **options):
        # Find the parent menu "Bookkeeping"
        parent = MenuItem.objects.filter(url_name__startswith='bookkeeping:').first()
        if parent:
            if parent.parent:
                parent = parent.parent
        
        if not parent:
            parent = MenuItem.objects.filter(title='記帳業務').first()
            if not parent:
                self.stdout.write(self.style.ERROR('Could not find parent menu "記帳業務"'))
                return

        self.stdout.write(f'Parent menu found: {parent.title} (ID: {parent.id})')

        menu, created = MenuItem.objects.get_or_create(
            parent=parent,
            title='營業稅申報',
            defaults={
                'url_name': 'bookkeeping:business_tax_list',
                'order': 80,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully added "營業稅申報" menu link.'))
        else:
            # Update values if it exists
            menu.url_name = 'bookkeeping:business_tax_list'
            menu.order = 80
            menu.save()
            self.stdout.write(self.style.WARNING('"營業稅申報" menu already existed. Updated.'))
