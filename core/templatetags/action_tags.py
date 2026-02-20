from django import template
from django.contrib.contenttypes.models import ContentType
from core.models import DocumentTemplate
from core.notifications.models import EmailTemplate, LineMessageTemplate

register = template.Library()

@register.simple_tag
def get_available_actions(obj):
    """
    Checks if there are any templates available for the given object.
    Returns a dictionary of available actions.
    """
    if not obj:
        return {}

    try:
        content_type = ContentType.objects.get_for_model(obj)
    except Exception:
        return {}

    actions = {
        'has_documents': False,
        'has_email': False,
        'has_line': False,
    }

    # Check for Document Templates (Word/PDF)
    # DocumentTemplate has 'model_content_type'
    if DocumentTemplate.objects.filter(model_content_type=content_type).exists():
        actions['has_documents'] = True

    # Check for Email Templates
    if EmailTemplate.objects.filter(model_content_type=content_type, is_active=True).exists():
        actions['has_email'] = True

    # Check for Line Templates
    if LineMessageTemplate.objects.filter(model_content_type=content_type, is_active=True).exists():
        actions['has_line'] = True

    return actions

@register.filter
def app_label(obj):
    return obj._meta.app_label

@register.filter
def model_name(obj):
    return obj._meta.model_name

@register.filter
def to_create_url(url_name):
    """Convert update/edit URL name to create URL name"""
    return url_name.replace('_update', '_create').replace('_edit', '_create')

@register.filter
def to_delete_url(url_name):
    """Convert update/edit URL name to delete URL name"""
    return url_name.replace('_update', '_delete').replace('_edit', '_delete')

@register.filter
def to_list_url(url_name):
    """Convert update/edit/create URL name to list URL name"""
    return url_name.replace('_update', '_list').replace('_edit', '_list').replace('_create', '_list')
