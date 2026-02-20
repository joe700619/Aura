from django.contrib import admin
from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('merchant_trade_no', 'total_amount', 'trade_date', 'rtn_code', 'item_name', 'has_shipping')
    list_filter = ('rtn_code', 'payment_type', 'has_shipping', 'trade_date')
    search_fields = ('merchant_trade_no', 'related_id', 'item_name')
    readonly_fields = ('trade_date', 'created_at', 'updated_at')
