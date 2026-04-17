_MANAGEMENT_GROUPS = ['CPA', 'management', 'Admin']


def user_permissions(request):
    """
    Adds permission flags to every template context.

    is_management_user  — True if user is in CPA / management / Admin (or superuser)
    is_hr_user          — True if user is in 人資組 (or management)
    """
    user = request.user
    if not user.is_authenticated:
        return {
            'is_management_user': False,
            'is_hr_user': False,
        }

    if user.is_superuser:
        return {
            'is_management_user': True,
            'is_hr_user': True,
        }

    group_names = set(user.groups.values_list('name', flat=True))
    is_management = bool(group_names & set(_MANAGEMENT_GROUPS))

    return {
        'is_management_user': is_management,
        'is_hr_user': is_management or '人資組' in group_names,
        'is_admin_user': 'Admin' in group_names,
    }
