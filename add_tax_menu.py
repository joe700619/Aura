import django
from django.conf import settings

django.setup()

from modules.system_config.models import MenuItem

def add_business_tax_menu():
    # Try finding the parent. We know the UI says "記帳業務" or "Bookkeeping"
    parent = MenuItem.objects.filter(url_name__startswith='bookkeeping:').first()
    
    if parent:
        # If it's a child, get its true parent
        parent = parent.parent if parent.parent else parent

    if not parent:
        print("Could not find Bookkeeping menu parent. Looking by title...")
        parent = MenuItem.objects.filter(title__icontains='記帳').first()
        if not parent:
             # Just create one if really not found
             parent, _ = MenuItem.objects.get_or_create(
                 title='記帳業務',
                 defaults={'order': 20}
             )

    print(f"Parent Menu is: {parent.title}")

    # Create the new menu item
    menu, created = MenuItem.objects.get_or_create(
        parent=parent,
        title='營業稅申報',
        defaults={
            'url_name': 'bookkeeping:business_tax_list',
            'order': 80,  # Place it at the end
        }
    )
    
    if created:
        print("Successfully created '營業稅申報' menu item!")
    else:
        print("'營業稅申報' menu item already exists.")

if __name__ == "__main__":
    add_business_tax_menu()
