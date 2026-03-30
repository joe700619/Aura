from django import forms
from django.template.loader import render_to_string
from django.db import models

class ModalSelectWidget(forms.TextInput):
    template_name = 'components/widgets/modal_select.html'

    def __init__(self, search_url, label_model=None, button_label=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_url = search_url
        self.label_model = label_model
        self.button_label = button_label

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        # Default label
        label = self.button_label or "請選擇..."

        # Try to fetch the label if value exists
        if value:
            if self.label_model:
                try:
                    obj = self.label_model.objects.get(pk=value)
                    # Try common name fields
                    if hasattr(obj, 'name'):
                        label = obj.name
                    elif hasattr(obj, 'title'):
                        label = obj.title
                    else:
                        label = str(obj)
                except self.label_model.DoesNotExist:
                    label = "未知項目"
        
        context['widget'].update({
            'search_url': self.search_url,
            'label': label,
            'value': value if value else '',
            'name': name,
            # widget template expects these
            'form_prefix': '', 
        })
        return context
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget as an HTML string."""
        context = self.get_context(name, value, attrs)
        return render_to_string(self.template_name, context['widget'])
