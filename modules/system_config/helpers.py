from .models import SystemParameter
from django.conf import settings

def get_system_param(key, default=None):
    """
    Retrieves a system parameter value.
    Prioritizes the database `SystemParameter`.
    Falls back to `django.conf.settings` if not found in DB.
    Finally returns `default` if strictly necessary.
    """
    # 1. Try Database
    try:
        param = SystemParameter.objects.get(key=key)
        if param.value:
            return param.value
    except SystemParameter.DoesNotExist:
        pass
    
    # 2. Try Django Settings
    if hasattr(settings, key):
        return getattr(settings, key)
        
    return default
