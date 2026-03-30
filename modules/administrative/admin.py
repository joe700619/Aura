from django.contrib import admin
from .models import TaxTemplate, TaxTaskInstance
from .models.document_receipt import DocumentReceipt
from .models.document_dispatch import DocumentDispatch, DocumentDispatchItem
from .models.seal_procurement import SealProcurement, SealProcurementItem
from .models.advance_payment import AdvancePayment, AdvancePaymentDetail


class DocumentDispatchItemInline(admin.TabularInline):
    model = DocumentDispatchItem
    extra = 0
    fields = ['customer', 'tax_id', 'address', 'postage', 'is_absorbed_by_customer', 'is_notified', 'is_deleted']
    readonly_fields = ['is_deleted']


@admin.register(DocumentDispatch)
class DocumentDispatchAdmin(admin.ModelAdmin):
    list_display = ['date', 'dispatch_method', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'dispatch_method']
    date_hierarchy = 'date'
    inlines = [DocumentDispatchItemInline]


@admin.register(DocumentReceipt)
class DocumentReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_date', 'customer', 'subject', 'category', 'status', 'is_deleted']
    list_filter = ['status', 'category', 'is_deleted']
    search_fields = ['subject', 'customer__name']
    date_hierarchy = 'receipt_date'

@admin.register(SealProcurement)
class SealProcurementAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'company_name', 'unified_business_no', 'seal_cost_subtotal', 'is_paid', 'is_deleted']
    list_filter = ['is_deleted', 'is_paid', 'transfer_to_inventory']
    search_fields = ['company_name', 'unified_business_no']
    date_hierarchy = 'created_at'

@admin.register(SealProcurementItem)
class SealProcurementItemAdmin(admin.ModelAdmin):
    list_display = ['procurement', 'movement_type', 'seal_type', 'quantity', 'unit_price', 'subtotal', 'is_deleted']
    list_filter = ['is_deleted', 'movement_type', 'seal_type']
    search_fields = ['procurement__company_name', 'name_or_address']

class AdvancePaymentDetailInline(admin.TabularInline):
    model = AdvancePaymentDetail
    extra = 0
    fields = ['is_customer_absorbed', 'customer', 'unified_business_no', 'reason', 'amount', 'payment_type', 'is_deleted']
    readonly_fields = ['is_deleted']

@admin.register(AdvancePayment)
class AdvancePaymentAdmin(admin.ModelAdmin):
    list_display = ['advance_no', 'date', 'applicant', 'total_amount', 'is_posted', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'is_posted', 'date']
    search_fields = ['advance_no', 'description']
    date_hierarchy = 'date'
    readonly_fields = ['advance_no', 'created_at', 'updated_at']
    inlines = [AdvancePaymentDetailInline]

@admin.register(AdvancePaymentDetail)
class AdvancePaymentDetailAdmin(admin.ModelAdmin):
    list_display = ['advance_payment', 'reason', 'amount', 'is_customer_absorbed', 'payment_type', 'is_deleted']
    list_filter = ['is_deleted', 'is_customer_absorbed', 'payment_type']
    search_fields = ['advance_payment__advance_no', 'reason', 'unified_business_no']

@admin.register(TaxTemplate)
class TaxTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_recurring', 'recurring_months', 'deadline_day', 'source_type']
    list_filter = ['is_recurring', 'source_type']
    search_fields = ['name']

@admin.register(TaxTaskInstance)
class TaxTaskInstanceAdmin(admin.ModelAdmin):
    list_display = ['title', 'template', 'year', 'month', 'deadline', 'is_completed', 'completed_clients', 'total_clients']
    list_filter = ['year', 'month', 'is_completed', 'template']
    search_fields = ['title']
    date_hierarchy = 'deadline'
