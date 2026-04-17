from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Account, Voucher, VoucherDetail, Receivable, FixedAsset, Collection, ReceivableNotification

@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('code',)
    list_per_page = 25

class VoucherDetailInline(admin.TabularInline):
    model = VoucherDetail
    extra = 2
    autocomplete_fields = ('account',)

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_no', 'date', 'status', 'description', 'created_by', 'is_deleted')
    list_filter = ('status', 'is_deleted', 'date')
    search_fields = ('voucher_no', 'description')
    inlines = [VoucherDetailInline]
    list_per_page = 25
    actions = ['restore_vouchers']

    def get_queryset(self, _request):
        return self.model._default_manager.all()

    @admin.action(description='還原選取的傳票（取消軟刪除）')
    def restore_vouchers(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'已成功還原 {updated} 筆傳票。')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):
    list_display = ('receivable_no', 'date', 'company_name', 'unified_business_no', 'assistant', 'is_deleted')
    list_filter = ('is_deleted',)
    search_fields = ('receivable_no', 'company_name', 'unified_business_no')
    actions = ['restore_receivables']
    list_per_page = 25

    def get_queryset(self, _request):
        return self.model._default_manager.all()

    @admin.action(description='還原選取的應收帳款（取消軟刪除）')
    def restore_receivables(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'已成功還原 {updated} 筆應收帳款。')

@admin.register(VoucherDetail)
class VoucherDetailAdmin(admin.ModelAdmin):
    list_display = ('voucher', 'account', 'debit', 'credit', 'company_id', 'department', 'project')
    list_filter = ('account__category',)
    search_fields = ('voucher__voucher_no', 'account__name', 'remark')
    list_per_page = 25

@admin.register(FixedAsset)
class FixedAssetAdmin(admin.ModelAdmin):
    list_display = ('asset_no', 'name', 'purchase_date', 'cost', 'status')
    list_filter = ('status', 'purchase_date')
    search_fields = ('asset_no', 'name')
    list_per_page = 25

@admin.register(ReceivableNotification)
class ReceivableNotificationAdmin(admin.ModelAdmin):
    list_display = ('receivable', 'threshold_days', 'channel', 'success', 'sent_at', 'error_message')
    list_filter = ('channel', 'threshold_days', 'success')
    search_fields = ('receivable__receivable_no', 'receivable__company_name')
    readonly_fields = ('receivable', 'threshold_days', 'channel', 'sent_at', 'success', 'error_message')
    ordering = ('-sent_at',)
    list_per_page = 25

    def has_add_permission(self, request):
        return False


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('collection_no', 'date', 'receivable', 'method', 'total', 'is_posted', 'is_deleted')
    list_filter = ('is_posted', 'method', 'is_deleted')
    search_fields = ('collection_no', 'receivable__company_name')
    actions = ['restore_collections']
    list_per_page = 25

    def get_queryset(self, _request):
        return self.model._default_manager.all()

    @admin.action(description='還原選取的收款紀錄（取消軟刪除）')
    def restore_collections(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'已成功還原 {updated} 筆收款紀錄。')
