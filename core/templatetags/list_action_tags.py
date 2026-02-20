from django import template
from django.contrib.contenttypes.models import ContentType
from core.notifications.models import EmailTemplate, LineMessageTemplate

register = template.Library()

@register.simple_tag
def get_list_available_actions(model_class):
    """
    Check which bulk actions are available for a given model in list view.
    Returns a dictionary of available actions.
    
    Args:
        model_class: The Django model class to check
        
    Returns:
        dict: {
            'has_excel': bool,  # Always True
            'has_email': bool,  # True if active EmailTemplate exists
            'has_line': bool,   # True if active LineMessageTemplate exists
        }
    """
    if not model_class:
        return {
            'has_excel': True,
            'has_email': False,
            'has_line': False,
        }
    
    try:
        content_type = ContentType.objects.get_for_model(model_class)
    except Exception:
        return {
            'has_excel': True,
            'has_email': False,
            'has_line': False,
        }
    
    actions = {
        'has_excel': True,  # Excel export is always available
        'has_email': False,
        'has_line': False,
    }
    
    # Check for Email Templates
    if EmailTemplate.objects.filter(model_content_type=content_type, is_active=True).exists():
        actions['has_email'] = True
    
    # Check for Line Templates
    if LineMessageTemplate.objects.filter(model_content_type=content_type, is_active=True).exists():
        actions['has_line'] = True
    
    return actions
