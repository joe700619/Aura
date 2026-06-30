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


def reactivate_employees(_modeladmin, _request, queryset):
    # Employee 用 is_active 做軟刪除（非 is_deleted），對應的還原動作
    queryset.update(is_active=True)
reactivate_employees.short_description = '重新啟用（還原）員工'


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
    
    actions = [reactivate_employees]

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

    def _soft_delete(self, obj):
        """
        從 admin 刪除員工時改為軟刪除（is_active=False），比照前端行為。

        Employee 的所有子檔（請假單/出勤/餘額…）FK 都是 CASCADE，
        admin 預設硬刪會把這些資料連帶清光、且不留痕跡。改軟刪可避免。
        """
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=['is_active', 'updated_at'])

    def delete_model(self, _request, obj):
        self._soft_delete(obj)

    def delete_queryset(self, _request, queryset):
        for obj in queryset:
            self._soft_delete(obj)


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

    def _soft_delete_with_rollback(self, obj):
        """
        從 admin 刪除請假單時，比照前端行為：回沖假期餘額 + 軟刪除。

        admin 預設是硬刪除，不會經過 model 的 cancel()，會導致已扣掉的
        used_hours 沒被退回（餘額對不起來）。這裡統一改走 cancel()。
        """
        obj.cancel()  # status -> cancelled 並回沖 used_hours（pending/approved 才退，idempotent）
        if not obj.is_deleted:
            obj.is_deleted = True
            obj.save(update_fields=['is_deleted', 'updated_at'])

    def delete_model(self, _request, obj):
        # change 頁面的「刪除」按鈕（單筆）
        self._soft_delete_with_rollback(obj)

    def delete_queryset(self, _request, queryset):
        # 列表頁的「刪除選取項目」批次 action
        for obj in queryset:
            self._soft_delete_with_rollback(obj)


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
    list_display = ['employee', 'date', 'minutes', 'day_type_label', 'is_approved', 'is_deleted', 'created_at']
    list_filter = ['is_approved', 'is_deleted']
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
