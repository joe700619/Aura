from django import template
from django.db.models import Q
from django.urls import resolve, reverse
from ..models import MenuItem

register = template.Library()

@register.inclusion_tag('layouts/components/menu_renderer.html', takes_context=True)
def render_dynamic_sidebar(context):
    request = context['request']
    user = request.user
    
    # 1. Get all active items
    all_items = MenuItem.objects.filter(is_active=True).select_related('parent').prefetch_related('roles')
    
    # 2. Filter by permissions
    visible_items = []
    for item in all_items:
        item_roles = item.roles.all()
        # If no roles defined, it's public (or for all logged-in users)
        if not item_roles:
            visible_items.append(item)
            continue
            
        # If roles defined, user must be authenticated and have at least one matching role
        if user.is_authenticated:
            if user.groups.filter(id__in=item_roles.values_list('id', flat=True)).exists() or user.is_superuser:
                visible_items.append(item)

    # 3. Build tree structure
    # Define a helper to check if an item is active based on current path
    current_path = request.path
    
    menu_tree = []
    # Create a map for easy parent lookup
    # Create a map for easy parent lookup
    item_map = {item.id: item for item in visible_items}
    
    # 3. Initialize helper attributes for ALL items first
    for item in visible_items:
        item.children_list = []
        item.is_active_path = False

        # Check path matching
        if item.url_name:
            try:
                from django.urls import resolve, reverse
                resolver_match = resolve(current_path)
                if resolver_match.url_name == item.url_name:
                    item.is_active_path = True
                
                item_url = reverse(item.url_name)
                if item_url != '/' and current_path.startswith(item_url):
                    item.is_active_path = True
            except:
                pass

    # 4. Build tree structure
    for item in visible_items:
        if item.parent_id:
            parent = item_map.get(item.parent_id)
            if parent:
                parent.children_list.append(item)
                # If child is active, parent should be too
                if item.is_active_path:
                    parent.is_active_path = True
        else:
            menu_tree.append(item)

    # Re-sort using the 'order' field
    menu_tree.sort(key=lambda x: x.order)
    for item in menu_tree:
        item.children_list.sort(key=lambda x: x.order)

    return {'menu_tree': menu_tree, 'request': request}
