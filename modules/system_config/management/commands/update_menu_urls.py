from django.core.management.base import BaseCommand
from modules.system_config.models import MenuItem

class Command(BaseCommand):
    help = 'Update menu item URL names to include namespaces'

    def handle(self, *args, **options):
        try:
            item = MenuItem.objects.get(url_name='employee_list')
            item.url_name = 'hr:employee_list'
            item.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated menu item "{item.title}" to use "hr:employee_list"'))
        except MenuItem.DoesNotExist:
            self.stdout.write(self.style.WARNING('Menu item with url_name="employee_list" not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating menu item: {e}'))
