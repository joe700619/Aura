from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Account, Voucher, VoucherDetail

@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('code',)

class VoucherDetailInline(admin.TabularInline):
    model = VoucherDetail
    extra = 2
    autocomplete_fields = ('account',)

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_no', 'date', 'status', 'description', 'created_by')
    list_filter = ('status', 'date')
    search_fields = ('voucher_no', 'description')
    inlines = [VoucherDetailInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(VoucherDetail)
class VoucherDetailAdmin(admin.ModelAdmin):
    list_display = ('voucher', 'account', 'debit', 'credit', 'company_id', 'department', 'project')
    list_filter = ('account__category',)
    search_fields = ('voucher__voucher_no', 'account__name', 'remark')
