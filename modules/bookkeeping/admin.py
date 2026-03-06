from django.contrib import admin
from .models import (
    BookkeepingClient, 
    GroupInvoice, 
    ConvenienceBagLog, 
    AccountingBookLog,
    TaxFilingSetting,
    TaxFilingYear,
    TaxFilingPeriod
)

@admin.register(BookkeepingClient)
class BookkeepingClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'acceptance_status', 'billing_status', 'service_type', 'client_source')
    list_filter = ('acceptance_status', 'billing_status', 'service_type', 'client_source')
    search_fields = ('name', 'tax_id')


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
