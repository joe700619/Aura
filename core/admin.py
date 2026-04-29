from django.contrib import admin, messages
from django.core.management import call_command
from .models import DocumentTemplate, ScheduledJob


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_content_type', 'uploaded_at')
    list_filter = ('model_content_type', 'uploaded_at')
    search_fields = ('name', 'description')


@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = ('name', 'command', 'cron_schedule', 'enabled',
                    'last_run_at', 'last_status')
    list_filter = ('enabled', 'last_status')
    search_fields = ('name', 'command', 'description')
    readonly_fields = ('last_run_at', 'last_status', 'last_message',
                       'created_at', 'updated_at')
    fieldsets = (
        ('任務資訊', {
            'fields': ('name', 'command', 'description', 'cron_schedule', 'enabled'),
        }),
        ('執行紀錄', {
            'fields': ('last_run_at', 'last_status', 'last_message'),
        }),
        ('系統', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['run_selected_jobs']

    @admin.action(description='立即執行選定的任務')
    def run_selected_jobs(self, request, queryset):
        for job in queryset:
            try:
                call_command(job.command)
                self.message_user(request, f'已執行：{job.name}', messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f'執行失敗 {job.name}：{e}', messages.ERROR)
