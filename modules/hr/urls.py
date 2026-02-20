"""
HR Module URL Configuration
"""
from django.urls import path
app_name = 'hr'
from .views.employee import (
    EmployeeListView,
    EmployeeCreateView,
    EmployeeUpdateView,
    EmployeeDeleteView,
    employee_submit_approval,
    employee_approve,
    employee_reject,
    employee_return,
    employee_cancel_approval,
)
from .views.api import EmployeeSearchApiView

urlpatterns = [
    # API
    path('api/employees/search/', EmployeeSearchApiView.as_view(), name='employee_search_api'),

    # Employee CRUD
    path('employees/', EmployeeListView.as_view(), name='employee_list'),
    path('employees/new/', EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee_delete'),
    
    # Employee Approval Actions
    path('employees/<int:pk>/submit-approval/', employee_submit_approval, name='employee_submit_approval'),
    path('employees/<int:pk>/approve/', employee_approve, name='employee_approve'),
    path('employees/<int:pk>/reject/', employee_reject, name='employee_reject'),
    path('employees/<int:pk>/return/', employee_return, name='employee_return'),
    path('employees/<int:pk>/cancel-approval/', employee_cancel_approval, name='employee_cancel_approval'),
]
