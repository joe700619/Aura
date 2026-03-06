from modules.system_config.models import MenuItem

try:
    root = MenuItem.objects.get(title='行政總務')
    MenuItem.objects.get_or_create(
        title='國稅局查帳通知', 
        defaults={
            'url_name': 'administrative:irs_audit_notice_list', 
            'parent': root, 
            'order': 100, 
            'icon_svg': '<svg class="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>'
        }
    )
    print("Menu item added successfully.")
except Exception as e:
    print(f"Error adding menu item: {e}")
