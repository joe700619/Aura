from django import template
from django.urls import resolve, reverse
from ..models import MenuItem

register = template.Library()

@register.inclusion_tag('layouts/components/menu_renderer.html', takes_context=True)
def render_dynamic_sidebar(context):
    request = context['request']
    user = request.user
    
    # 1. Get all active items
    all_items = MenuItem.objects.filter(is_active=True).select_related('parent')

    # 2. Filter by permissions
    visible_items = []
    for item in all_items:
        if not user.is_authenticated:
            continue

        # Superuser sees everything
        if user.is_superuser:
            visible_items.append(item)
            continue

        if item.required_permission:
            # Has a required permission: show only if user has it
            if user.has_perm(item.required_permission):
                visible_items.append(item)
        else:
            # No permission required: visible to all logged-in users
            visible_items.append(item)

    # 3. Initialize attributes & check active path
    current_path = request.path
    item_map = {item.id: item for item in visible_items}

    for item in visible_items:
        item.children_list = []
        item.is_active_path = False
        if item.url_name:
            try:
                resolver_match = resolve(current_path)
                if resolver_match.url_name == item.url_name:
                    item.is_active_path = True
                item_url = reverse(item.url_name)
                if item_url != '/' and current_path.startswith(item_url):
                    item.is_active_path = True
            except Exception:
                pass

    # 4. Build tree
    menu_tree = []
    for item in visible_items:
        if item.parent_id:
            parent = item_map.get(item.parent_id)
            if parent:
                parent.children_list.append(item)
                if item.is_active_path:
                    parent.is_active_path = True
        else:
            menu_tree.append(item)

    # 5. Remove section headers that have no visible children
    #    (top-level items with no url_name and no children should not appear)
    menu_tree = [
        item for item in menu_tree
        if item.url_name or item.children_list
    ]

    # Re-sort using the 'order' field
    menu_tree.sort(key=lambda x: x.order)
    for item in menu_tree:
        item.children_list.sort(key=lambda x: x.order)

    return {'menu_tree': menu_tree, 'request': request}
