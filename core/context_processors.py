from django.core.cache import cache

_MANAGEMENT_GROUPS = ['CPA', 'management', 'Admin']

# 5 分鐘 cache：使用者權限改變後最多 5 分鐘生效
_PERMISSION_CACHE_TTL = 300


def user_permissions(request):
    """
    Adds permission flags to every template context.

    is_management_user  — True if user is in CPA / management / Admin (or superuser)
    is_hr_user          — True if user is in 人資組 (or management)

    Per-user 5 分鐘 cache，避免每個 request 都查 user.groups。
    若使用者 group 異動，最多 5 分鐘後生效。
    """
    user = request.user
    if not user.is_authenticated:
        return {
            'is_management_user': False,
            'is_hr_user': False,
            'is_admin_user': False,
        }

    if user.is_superuser:
        return {
            'is_management_user': True,
            'is_hr_user': True,
            'is_admin_user': True,
        }

    cache_key = f'user_permissions:{user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    group_names = set(user.groups.values_list('name', flat=True))
    is_management = bool(group_names & set(_MANAGEMENT_GROUPS))

    result = {
        'is_management_user': is_management,
        'is_hr_user': is_management or '人資組' in group_names,
        'is_admin_user': 'Admin' in group_names,
    }
    cache.set(cache_key, result, _PERMISSION_CACHE_TTL)
    return result
