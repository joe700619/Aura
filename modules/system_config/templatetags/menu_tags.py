from django import template
from django.core.cache import cache
from django.urls import resolve, reverse
from ..models import MenuItem

register = template.Library()


# 快取版本：MenuItem.save() 訊號會更新此版本號讓 cache 失效（見 models.py）
SIDEBAR_CACHE_VERSION_KEY = 'sidebar_menu_version'
SIDEBAR_CACHE_TTL = 300  # 5 分鐘


def _get_visible_items_cached(user):
    """
    回傳 user 可見的 MenuItem id 集合 + items dict（per-user 快取 5 分鐘）。
    cache key 包含 user.id 與 menu version，新增/改選單或改權限後自然失效。
    """
    if not user.is_authenticated:
        return []

    version = cache.get(SIDEBAR_CACHE_VERSION_KEY) or 1
    cache_key = f'sidebar_visible:{user.pk}:v{version}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    all_items = list(MenuItem.objects.filter(is_active=True).select_related('parent'))
    visible_items = []
    for item in all_items:
        if user.is_superuser:
            visible_items.append(item)
        elif item.required_permission:
            if user.has_perm(item.required_permission):
                visible_items.append(item)
        else:
            visible_items.append(item)

    cache.set(cache_key, visible_items, SIDEBAR_CACHE_TTL)
    return visible_items


@register.inclusion_tag('layouts/components/menu_renderer.html', takes_context=True)
def render_dynamic_sidebar(context):
    request = context['request']
    user = request.user

    visible_items = _get_visible_items_cached(user)

    # 3. Initialize attributes & check active path
    current_path = request.path
    item_map = {item.id: item for item in visible_items}

    # 同一個 path 只解析一次，不在迴圈內重複 resolve
    try:
        current_url_name = resolve(current_path).url_name
    except Exception:
        current_url_name = None

    for item in visible_items:
        item.children_list = []
        item.is_active_path = False
        if item.url_name:
            try:
                if current_url_name and current_url_name == item.url_name:
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
