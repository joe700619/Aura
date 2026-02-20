"""
Workflow Admin Configuration
"""
from django.contrib import admin
from .models import (
    WorkflowTemplate,
    WorkflowStep,
    ApproverDelegate,
    ApprovalRequest,
    ApprovalHistory,
    ApprovalReminder
)


class WorkflowStepInline(admin.TabularInline):
    """流程步驟內聯編輯"""
    model = WorkflowStep
    extra = 1
    fields = [
        'step_number', 'step_name',
        'approver_user', 'approver_role', 'approver_field',
        'can_approve', 'can_reject', 'can_return'
    ]
    ordering = ['step_number']


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    """工作流程模板管理"""
    list_display = ['name', 'code', 'is_active', 'reminder_hours', 'max_reminders', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('基本資訊', {
            'fields': ['name', 'code', 'description', 'is_active']
        }),
        ('提醒設定', {
            'fields': ['reminder_hours', 'max_reminders']
        }),
        ('系統資訊', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [WorkflowStepInline]


@admin.register(ApproverDelegate)
class ApproverDelegateAdmin(admin.ModelAdmin):
    """代理人設定管理"""
    list_display = ['user', 'delegate', 'start_date', 'end_date', 'workflow_template', 'is_active', 'is_valid_display']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['user__username', 'user__first_name', 'user__last_name',
                    'delegate__username', 'delegate__first_name', 'delegate__last_name']
    date_hierarchy = 'start_date'
    
    fieldsets = [
        ('代理資訊', {
            'fields': ['user', 'delegate', 'workflow_template']
        }),
        ('有效期間', {
            'fields': ['start_date', 'end_date', 'is_active']
        }),
    ]
    
    def is_valid_display(self, obj):
        """顯示是否目前有效"""
        return obj.is_valid_now()
    is_valid_display.boolean = True
    is_valid_display.short_description = '目前有效'


class ApprovalHistoryInline(admin.TabularInline):
    """核准歷史內聯顯示"""
    model = ApprovalHistory
    extra = 0
    can_delete = False
    readonly_fields = ['action', 'actor', 'actor_as_delegate', 'step', 'action_date', 'comments']
    fields = ['action_date', 'action', 'actor', 'actor_as_delegate', 'step', 'comments']
    ordering = ['-action_date']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    """核准請求管理（主要用於查詢）"""
    list_display = ['content_object', 'workflow_template', 'status', 'requester', 
                   'current_step', 'submit_date', 'completed_date']
    list_filter = ['status', 'workflow_template', 'submit_date']
    search_fields = ['requester__username', 'requester__first_name', 'requester__last_name']
    date_hierarchy = 'request_date'
    readonly_fields = ['content_type', 'object_id', 'content_object', 'request_date', 
                      'submit_date', 'completed_date', 'reminder_count', 'last_reminder_sent']
    
    fieldsets = [
        ('核准物件', {
            'fields': ['content_type', 'object_id', 'content_object']
        }),
        ('流程資訊', {
            'fields': ['workflow_template', 'current_step', 'status']
        }),
        ('申請資訊', {
            'fields': ['requester', 'request_date', 'submit_date', 'completed_date']
        }),
        ('提醒資訊', {
            'fields': ['reminder_count', 'last_reminder_sent'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [ApprovalHistoryInline]
    
    def has_add_permission(self, request):
        """不允許直接新增，應該由系統自動建立"""
        return False


@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    """核准歷史管理（主要用於查詢）"""
    list_display = ['approval_request', 'action', 'actor', 'actor_as_delegate', 
                   'step', 'action_date', 'email_sent', 'line_sent']
    list_filter = ['action', 'action_date', 'email_sent', 'line_sent']
    search_fields = ['actor__username', 'actor__first_name', 'actor__last_name', 'comments']
    date_hierarchy = 'action_date'
    readonly_fields = ['approval_request', 'step', 'action', 'actor', 'actor_as_delegate', 
                      'action_date', 'comments', 'email_sent', 'line_sent']
    
    def has_add_permission(self, request):
        """不允許直接新增"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """不允許刪除歷史記錄"""
        return False


@admin.register(ApprovalReminder)
class ApprovalReminderAdmin(admin.ModelAdmin):
    """提醒記錄管理（主要用於查詢）"""
    list_display = ['approval_request', 'recipient', 'reminder_number', 'sent_date', 
                   'email_sent', 'line_sent']
    list_filter = ['sent_date', 'email_sent', 'line_sent']
    search_fields = ['recipient__username', 'recipient__first_name', 'recipient__last_name']
    date_hierarchy = 'sent_date'
    readonly_fields = ['approval_request', 'recipient', 'sent_date', 'reminder_number', 
                      'email_sent', 'line_sent']
    
    def has_add_permission(self, request):
        """不允許直接新增"""
        return False
