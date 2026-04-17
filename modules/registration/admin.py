from django.contrib import admin
from .models import ClientAssessment, CaseAssessment, Shareholder, ShareholderRegister, EquityTransaction, CompanyFiling, Progress, VATEntityChange


def restore_deleted(_modeladmin, _request, queryset):
    queryset.update(is_deleted=False)
restore_deleted.short_description = '還原已刪除的資料'


@admin.register(ClientAssessment)
class ClientAssessmentAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'unified_business_no', 'risk_level', 'is_deleted', 'created_at']
    list_filter = ['risk_level', 'is_deleted']
    search_fields = ['company_name', 'unified_business_no', 'main_contact']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        # 顯示全部資料（包含已軟刪除），方便在 admin 找回
        return self.model._default_manager.all()


@admin.register(CaseAssessment)
class CaseAssessmentAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'unified_business_no', 'risk_level', 'is_completed', 'is_deleted', 'created_at']
    list_filter = ['risk_level', 'is_completed', 'is_deleted']
    search_fields = ['company_name', 'unified_business_no', 'registration_no']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(Shareholder)
class ShareholderAdmin(admin.ModelAdmin):
    list_display = ['name', 'id_number', 'nationality', 'is_active', 'is_deleted', 'created_at']
    list_filter = ['nationality', 'is_active', 'is_deleted']
    search_fields = ['name', 'id_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(ShareholderRegister)
class ShareholderRegisterAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'unified_business_no', 'service_status', 'completion_status', 'is_deleted', 'created_at']
    list_filter = ['service_status', 'completion_status', 'is_deleted']
    search_fields = ['company_name', 'unified_business_no']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(EquityTransaction)
class EquityTransactionAdmin(admin.ModelAdmin):
    list_display = ['shareholder_name', 'shareholder_register', 'transaction_date', 'transaction_reason', 'is_completed', 'is_deleted', 'created_at']
    list_filter = ['organization_type', 'transaction_reason', 'is_completed', 'is_deleted']
    search_fields = ['shareholder_name', 'shareholder_id_number', 'shareholder_register__company_name', 'registration_no']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ['registration_no', 'company_name', 'unified_business_no', 'main_contact', 'progress_status', 'acceptance_date', 'is_deleted', 'created_at']
    list_filter = ['progress_status', 'mandate_return', 'is_deleted']
    search_fields = ['registration_no', 'company_name', 'unified_business_no', 'main_contact']
    readonly_fields = ['registration_no', 'created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(CompanyFiling)
class CompanyFilingAdmin(admin.ModelAdmin):
    list_display = ['filing_no', 'company_name', 'unified_business_no', 'filing_method', 'fee', 'is_deleted', 'created_at']
    list_filter = ['filing_method', 'is_deleted']
    search_fields = ['filing_no', 'company_name', 'unified_business_no', 'main_contact']
    readonly_fields = ['filing_no', 'created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()


@admin.register(VATEntityChange)
class VATEntityChangeAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'unified_business_no', 'registration_no', 'assistant_name', 'is_completed', 'closed_at', 'is_deleted', 'created_at']
    list_filter = ['is_completed', 'is_deleted']
    search_fields = ['company_name', 'unified_business_no', 'registration_no', 'assistant_name']
    readonly_fields = ['created_at', 'updated_at']
    actions = [restore_deleted]

    def get_queryset(self, _request):
        return self.model._default_manager.all()
