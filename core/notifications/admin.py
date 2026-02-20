from django.contrib import admin
from .models import EmailTemplate, EmailLog, LineMessageTemplate, LineMessageLog

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'subject', 'model_content_type', 'is_active', 'updated_at')
    search_fields = ('name', 'code', 'subject')
    list_filter = ('is_active', 'model_content_type', 'created_at')

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'template', 'status', 'sent_at')
    list_filter = ('status', 'sent_at', 'template')
    readonly_fields = ('created_at', 'sent_at', 'error_message')
    search_fields = ('recipient', 'subject')

@admin.register(LineMessageTemplate)
class LineMessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'message_type', 'model_content_type', 'is_active', 'updated_at')
    search_fields = ('name', 'code')
    list_filter = ('message_type', 'is_active', 'model_content_type')

@admin.register(LineMessageLog)
class LineMessageLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_line_id', 'template', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    readonly_fields = ('created_at', 'sent_at', 'error_message')
    search_fields = ('recipient_line_id',)
