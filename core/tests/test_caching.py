"""
驗證批次 4 的 cache 機制：
- sidebar 選單 cache（per-user、自動失效）
- SystemParameter cache（自動失效）
- user_permissions context_processor cache
"""
import pytest
from django.core.cache import cache


# =============================================================================
# Sidebar 選單 cache
# =============================================================================
@pytest.mark.django_db
class TestSidebarCache:

    def test_sidebar_cache_returns_same_items_on_warm_call(self, superuser):
        """暖快取應回傳和冷快取一樣的結果"""
        from modules.system_config.templatetags.menu_tags import _get_visible_items_cached
        cache.clear()

        items_cold = _get_visible_items_cached(superuser)
        items_warm = _get_visible_items_cached(superuser)

        assert len(items_cold) == len(items_warm)

    def test_menu_save_bumps_sidebar_version(self, superuser):
        """新增/更新 MenuItem 應 bump sidebar cache version"""
        from modules.system_config.models import MenuItem
        from modules.system_config.templatetags.menu_tags import _get_visible_items_cached

        cache.clear()
        _get_visible_items_cached(superuser)  # warm cache
        v_before = cache.get('sidebar_menu_version') or 1

        MenuItem.objects.create(title='測試選單', url_name='', order=999)
        v_after = cache.get('sidebar_menu_version') or 1

        assert v_after > v_before

    def test_menu_delete_bumps_sidebar_version(self, superuser):
        from modules.system_config.models import MenuItem

        item = MenuItem.objects.create(title='待刪除選單', url_name='', order=998)
        v_before = cache.get('sidebar_menu_version') or 1
        item.delete()
        v_after = cache.get('sidebar_menu_version') or 1

        assert v_after > v_before

    def test_unauthenticated_user_returns_empty(self, db):
        """未登入應回傳空 list（不打 DB 也不 cache）"""
        from django.contrib.auth.models import AnonymousUser
        from modules.system_config.templatetags.menu_tags import _get_visible_items_cached

        result = _get_visible_items_cached(AnonymousUser())
        assert result == []


# =============================================================================
# SystemParameter cache
# =============================================================================
@pytest.mark.django_db
class TestSystemParamCache:

    def test_get_param_returns_db_value(self):
        from modules.system_config.helpers import get_system_param
        from modules.system_config.models import SystemParameter

        cache.clear()
        SystemParameter.objects.create(key='TEST_KEY', value='from_db')
        assert get_system_param('TEST_KEY') == 'from_db'

    def test_get_param_falls_back_to_settings(self, settings):
        from modules.system_config.helpers import get_system_param
        cache.clear()
        settings.MY_TEST_FALLBACK = 'from_settings'
        assert get_system_param('MY_TEST_FALLBACK') == 'from_settings'

    def test_get_param_returns_default_when_missing(self):
        from modules.system_config.helpers import get_system_param
        cache.clear()
        assert get_system_param('NONEXISTENT_KEY', 'fallback') == 'fallback'

    def test_param_save_bumps_version(self):
        """SystemParameter 變動 → version bump → cache 自動失效"""
        from modules.system_config.helpers import get_system_param
        from modules.system_config.models import SystemParameter

        cache.clear()
        SystemParameter.objects.create(key='VERSIONED_KEY', value='v1')
        assert get_system_param('VERSIONED_KEY') == 'v1'

        v_before = cache.get('system_param_version') or 1

        SystemParameter.objects.filter(key='VERSIONED_KEY').update(value='v2')
        # update() 不觸發 signal，要直接 save
        sp = SystemParameter.objects.get(key='VERSIONED_KEY')
        sp.save()

        v_after = cache.get('system_param_version') or 1
        assert v_after > v_before


# =============================================================================
# user_permissions context_processor
# =============================================================================
@pytest.mark.django_db
class TestUserPermissionsCache:

    def test_anonymous_user_returns_false_flags(self, rf):
        from core.context_processors import user_permissions
        from django.contrib.auth.models import AnonymousUser
        request = rf.get('/')
        request.user = AnonymousUser()
        result = user_permissions(request)
        assert result['is_management_user'] is False
        assert result['is_hr_user'] is False

    def test_superuser_gets_all_flags_true(self, rf, superuser):
        from core.context_processors import user_permissions
        request = rf.get('/')
        request.user = superuser
        result = user_permissions(request)
        assert result['is_management_user'] is True
        assert result['is_hr_user'] is True
        assert result['is_admin_user'] is True

    def test_normal_user_management_groups(self, rf, user):
        from core.context_processors import user_permissions
        from django.contrib.auth.models import Group

        cache.clear()
        cpa_group, _ = Group.objects.get_or_create(name='CPA')
        user.groups.add(cpa_group)

        request = rf.get('/')
        request.user = user
        result = user_permissions(request)

        assert result['is_management_user'] is True


@pytest.fixture
def rf():
    """Django RequestFactory"""
    from django.test import RequestFactory
    return RequestFactory()
