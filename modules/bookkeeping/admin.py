from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import (
    BookkeepingClient, 
    GroupInvoice, 
    ConvenienceBagLog, 
    AccountingBookLog,
    TaxFilingSetting,
    TaxFilingYear,
    TaxFilingPeriod,
    IndustryTaxRate
)

@admin.register(BookkeepingClient)
class BookkeepingClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'acceptance_status', 'billing_status', 'service_type', 'client_source', 'is_deleted')
    list_filter = ('is_deleted', 'acceptance_status', 'billing_status', 'service_type', 'client_source')
    search_fields = ('name', 'tax_id')
    actions = ['restore_clients']

    @admin.action(description='還原已刪除的記帳客戶')
    def restore_clients(self, request, queryset):
        updated = queryset.filter(is_deleted=True).update(is_deleted=False)
        self.message_user(request, f'已還原 {updated} 筆記帳客戶。')


@admin.register(GroupInvoice)
class GroupInvoiceAdmin(admin.ModelAdmin):
    list_display = ('client', 'invoice_type', 'quantity')
    list_filter = ('invoice_type',)


@admin.register(ConvenienceBagLog)
class ConvenienceBagLogAdmin(admin.ModelAdmin):
    list_display = ('client', 'date', 'quantity')


@admin.register(AccountingBookLog)
class AccountingBookLogAdmin(admin.ModelAdmin):
    list_display = ('client', 'date', 'year', 'cd_rom', 'sales_invoice_qty')
    list_filter = ('year', 'cd_rom')


@admin.register(TaxFilingSetting)
class TaxFilingSettingAdmin(admin.ModelAdmin):
    list_display = ('client', 'form_type', 'filing_frequency', 'is_audited')
    list_filter = ('form_type', 'filing_frequency', 'is_audited')
    search_fields = ('client__name',)


@admin.register(TaxFilingYear)
class TaxFilingYearAdmin(admin.ModelAdmin):
    list_display = ('client', 'year')
    list_filter = ('year',)
    search_fields = ('client__name',)


@admin.register(TaxFilingPeriod)
class TaxFilingPeriodAdmin(admin.ModelAdmin):
    list_display = ('year_record', 'period_start_month', 'sales_amount', 'payable_tax', 'is_filed', 'filing_date')
    list_filter = ('is_filed', 'period_start_month')
    search_fields = ('year_record__client__name',)

@admin.register(IndustryTaxRate)
class IndustryTaxRateAdmin(ImportExportModelAdmin):
    list_display = ('industry_code', 'industry_name', 'applicable_year', 'book_review_profit_rate', 'net_profit_rate', 'income_standard')
    search_fields = ('industry_code', 'industry_name')
    list_filter = ('applicable_year',)
    ordering = ('-applicable_year', 'industry_code')
