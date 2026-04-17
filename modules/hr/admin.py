from django.contrib import admin
from .models import Employee, AdvancePayment, AttendanceRecord, LeaveBalance, LeaveType, LeaveRequest, SalaryStructure, OvertimeRecord, PayrollRecord, InsuranceBracket


def restore_deleted(_modeladmin, _request, queryset):
    queryset.update(is_deleted=False)
restore_deleted.short_description = '還原已刪除的資料'


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
        ('系統帳號', {
            'fields': ('user',),
        }),
        ('系統資訊', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AdvancePayment)
class AdvancePaymentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date_applied', 'amount', 'status', 'is_deleted', 'created_at']
    list_filter = ['status', 'is_deleted']
    search_fields = ['employee__name', 'reason']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'clock_in', 'clock_out', 'source', 'is_deleted', 'created_at']
    list_filter = ['source', 'is_deleted']
    search_fields = ['employee__name', 'employee__employee_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'entitled_hours', 'used_hours', 'is_deleted', 'created_at']
    list_filter = ['leave_type', 'year', 'is_deleted']
    search_fields = ['employee__name', 'employee__employee_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_paid', 'max_hours_per_year', 'requires_doc', 'sort_order', 'is_deleted', 'created_at']
    list_filter = ['is_paid', 'requires_doc', 'is_deleted']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_datetime', 'end_datetime', 'total_hours', 'status', 'is_deleted', 'created_at']
    list_filter = ['status', 'leave_type', 'is_deleted']
    search_fields = ['employee__name', 'leave_type__name']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ['employee', 'base_salary', 'effective_date', 'is_current', 'is_deleted', 'created_at']
    list_filter = ['is_current', 'is_deleted']
    search_fields = ['employee__name']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(OvertimeRecord)
class OvertimeRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'hours', 'rate', 'is_approved', 'is_deleted', 'created_at']
    list_filter = ['is_approved', 'rate', 'is_deleted']
    search_fields = ['employee__name', 'employee__employee_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'year_month', 'gross_salary', 'net_salary', 'is_finalized', 'is_deleted', 'created_at']
    list_filter = ['is_finalized', 'is_deleted']
    search_fields = ['employee__name', 'employee__employee_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(InsuranceBracket)
class InsuranceBracketAdmin(admin.ModelAdmin):
    list_display = ['level_name', 'insured_salary', 'labor_employee', 'labor_employer', 'health_employee', 'health_employer', 'pension_employer', 'is_deleted', 'created_at']
    list_filter = ['is_deleted']
    search_fields = ['level_name']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()
