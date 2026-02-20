# View Class Scaffold for Standard List View
# Copy this code and customize for your model

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from core.mixins import ListActionMixin
from .models import YourModel  # Replace with your model

class YourModelListView(ListActionMixin, LoginRequiredMixin, ListView):
    """
    Standard list view with automatic bulk actions (Excel, Email, Line).
    
    Checklist:
    - [ ] Import your model
    - [ ] Update class name
    - [ ] Set model attribute
    - [ ] Set template_name
    - [ ] Set context_object_name (must match template)
    - [ ] Set create_button_label (optional)
    - [ ] Add to urls.py
    """
    model = YourModel
    template_name = 'yourapp/yourmodel_list.html'
    context_object_name = 'yourmodels'  # MUST match {% for obj in CONTEXT_OBJECT_NAME %}
    paginate_by = 20
    
    # Optional: Customize the create button label
    create_button_label = '新增YOUR_MODEL'
    
    # Optional: Override queryset for filtering
    def get_queryset(self):
        queryset = super().get_queryset()
        # Add your custom filtering here
        # Example: queryset = queryset.filter(is_active=True)
        return queryset.order_by('-created_at')


# URLs Configuration Template
# Add this to your urls.py:

"""
from django.urls import path
from .views import YourModelListView

urlpatterns = [
    path('yourmodels/', YourModelListView.as_view(), name='yourmodel_list'),
    # ... other paths
]
"""
