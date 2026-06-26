from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, DateWidget, TimeWidget
from .models import Employee, AdvancePayment, AttendanceRecord, LeaveBalance, LeaveType, LeaveRequest, SalaryStructure, OvertimeRecord, PayrollRecord, InsuranceBracket


class AttendanceResource(resources.ModelResource):
    """
    出勤紀錄匯入/匯出。

    用途：批次匯入測試打卡資料，再跑薪資計算（PayrollRecord.calculate）
    對照遲到扣款等結果是否符合預期。

    匯入規則：
    - 「員工編號」對應到既有員工（找不到會報錯，不會新建員工）
    - 以（員工 + 日期）為識別鍵：同一員工同一天重複匯入會「更新」既有紀錄，不會新增重複列
    - 上/下班打卡格式為 HH:MM（例：08:30）；留空代表缺卡
    - 來源留空時預設為「補卡」
    """

    employee = fields.Field(
        column_name='員工編號',
        attribute='employee',
        widget=ForeignKeyWidget(Employee, field='employee_number'),
    )
    employee_name = fields.Field(
        column_name='員工姓名',
        attribute='employee__name',
        readonly=True,
    )
    date = fields.Field(
        column_name='日期',
        attribute='date',
        widget=DateWidget(format='%Y-%m-%d'),
    )
    clock_in = fields.Field(
        column_name='上班打卡',
        attribute='clock_in',
        widget=TimeWidget(format='%H:%M'),
    )
    clock_out = fields.Field(
        column_name='下班打卡',
        attribute='clock_out',
        widget=TimeWidget(format='%H:%M'),
    )
    source = fields.Field(column_name='來源', attribute='source')
    note = fields.Field(column_name='備註', attribute='note')

    class Meta:
        model = AttendanceRecord
        import_id_fields = ('employee', 'date')
        fields = ('employee', 'employee_name', 'date', 'clock_in', 'clock_out', 'source', 'note')
        export_order = fields
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        # 來源留空時預設為「補卡」（批次匯入多為人工補登）
        if not row.get('來源'):
            row['來源'] = 'makeup'


def restore_deleted(_modeladmin, _request, queryset):
    queryset.update(is_deleted=False)
restore_deleted.short_description = '還原已刪除的資料'


@admin.register(Employee)
class EmployeeAdmin(ImportExportModelAdmin):
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
class AttendanceRecordAdmin(ImportExportModelAdmin):
    resource_class = AttendanceResource
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
class LeaveTypeAdmin(ImportExportModelAdmin):
    list_display = ['code', 'name', 'pay_rate', 'max_hours_per_year', 'requires_doc', 'sort_order', 'is_deleted', 'created_at']
    list_filter = ['pay_rate', 'requires_doc', 'is_deleted']
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
class SalaryStructureAdmin(ImportExportModelAdmin):
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
class InsuranceBracketAdmin(ImportExportModelAdmin):
    list_display = ['level_name', 'insured_salary', 'labor_employee', 'labor_employer', 'health_employee', 'health_employer', 'pension_employer', 'is_deleted', 'created_at']
    list_filter = ['is_deleted']
    search_fields = ['level_name']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()
