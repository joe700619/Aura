from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import Customer, Contact

# print("DEBUG: Loading Customer Admin")

@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'tax_id', 'contact_person', 'phone', 'source', 'is_deleted', 'created_at')
    search_fields = ('name', 'tax_id', 'contact_person', 'phone', 'mobile', 'email')
    list_filter = ('is_deleted', 'source', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['soft_delete_action', 'restore_action']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'tax_id', 'source', 'line_id', 'room_id', 'is_deleted')
        }),
        ('聯絡資訊', {
            'fields': ('contact_person', 'phone', 'mobile', 'email')
        }),
        ('地址資訊', {
            'fields': ('registered_zip', 'registered_address', 'correspondence_zip', 'correspondence_address')
        }),
        ('帳務資訊', {
            'fields': ('bank_account_last5', 'labor_ins_code', 'health_ins_code')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            # 'classes': ('collapse',)
        }),
    )

    @admin.action(description='標記為刪除 (Soft Delete)')
    def soft_delete_action(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'{updated} 筆資料已標記為刪除。')

    @admin.action(description='復原刪除 (Restore)')
    def restore_action(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'{updated} 筆資料已復原。')

@admin.register(Contact)
class ContactAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'customer', 'phone', 'mobile', 'email', 'is_deleted')
    search_fields = ('name', 'customer__name', 'phone', 'mobile', 'email')
    list_filter = ('is_deleted', 'customer',)
    autocomplete_fields = ['customer']
    actions = ['soft_delete_action', 'restore_action']

    @admin.action(description='標記為刪除 (Soft Delete)')
    def soft_delete_action(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'{updated} 筆資料已標記為刪除。')

    @admin.action(description='復原刪除 (Restore)')
    def restore_action(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'{updated} 筆資料已復原。')

