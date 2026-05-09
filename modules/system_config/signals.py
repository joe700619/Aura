"""
system_config signals。

MenuItem / SystemParameter 變動時，bump 對應 cache 版本，
讓 sidebar / 系統設定的快取自然失效（next request 重建）。
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import MenuItem, SystemParameter


SIDEBAR_CACHE_VERSION_KEY = 'sidebar_menu_version'
SYSTEM_PARAM_CACHE_VERSION_KEY = 'system_param_version'


def _bump(key):
    """
    版本 +1。cache.incr 不存在 key 時會 raise，所以先 set 再 incr。
    """
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 2)  # 從 2 開始（1 是 cache miss 預設）


@receiver([post_save, post_delete], sender=MenuItem)
def bump_sidebar_cache(sender, **kwargs):
    """選單變更 → 全使用者 sidebar cache 失效"""
    _bump(SIDEBAR_CACHE_VERSION_KEY)


@receiver([post_save, post_delete], sender=SystemParameter)
def bump_system_param_cache(sender, **kwargs):
    """SystemParameter 變更 → cache 失效"""
    _bump(SYSTEM_PARAM_CACHE_VERSION_KEY)
