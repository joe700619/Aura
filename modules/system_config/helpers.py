from django.conf import settings
from django.core.cache import cache

from .models import SystemParameter


# 用 sentinel 區分「快取未命中」與「快取命中且值為 None」
_MISS = object()
_CACHE_TTL = 300  # 5 分鐘
_VERSION_KEY = 'system_param_version'


def _get_version():
    """signal 在 SystemParameter save/delete 時 incr 此版本號讓 cache 自然失效"""
    return cache.get(_VERSION_KEY) or 1


def get_system_param(key, default=None):
    """
    Retrieves a system parameter value.
    Prioritizes the database `SystemParameter`.
    Falls back to `django.conf.settings` if not found in DB.
    Finally returns `default` if strictly necessary.

    Per-key 5 分鐘 cache。SystemParameter 改動會觸發 signal bump version 自動失效。
    """
    cache_key = f'sysparam:{_get_version()}:{key}'
    cached = cache.get(cache_key, _MISS)
    if cached is not _MISS:
        # 命中（None 也算有效命中）
        return cached if cached is not None else default

    # 1. Try Database
    value = None
    try:
        param = SystemParameter.objects.get(key=key)
        if param.value:
            value = param.value
    except SystemParameter.DoesNotExist:
        pass

    # 2. Fallback to Django settings
    if value is None and hasattr(settings, key):
        value = getattr(settings, key)

    # cache the resolved value（即使是 None 也快取，避免重複打 DB）
    cache.set(cache_key, value, _CACHE_TTL)
    return value if value is not None else default
