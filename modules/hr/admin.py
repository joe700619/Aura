from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_number',
        'name',
        'gender',
        'team',
        'employment_status',
        'hire_date',
        'is_active'
    ]
    list_filter = ['employment_status', 'team', 'gender', 'is_active']
    search_fields = ['employee_number', 'name', 'id_number', 'email']
    readonly_fields = ['employee_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('基本資料', {
            'fields': ('employee_number', 'name', 'gender', 'id_number', 'line_id', 'extension')
        }),
        ('通訊方式', {
            'fields': ('phone', 'address', 'email')
        }),
        ('在職狀態', {
            'fields': ('employment_status', 'hire_date', 'resignation_date', 'team')
        }),
        ('系統資訊', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
