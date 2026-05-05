from django.contrib import admin

from .models import (
    Case, CaseTask, CaseReply, CaseAttachment,
    CaseAccessToken, CaseNotificationPreference, CaseNotificationLog,
)


class CaseTaskInline(admin.TabularInline):
    model = CaseTask
    extra = 0
    fields = ('title', 'assignee_type', 'due_date', 'is_done', 'is_hidden', 'order')


class CaseReplyInline(admin.TabularInline):
    model = CaseReply
    extra = 0
    fields = ('author_type', 'author_user', 'author_display_name', 'content', 'created_at')
    readonly_fields = ('created_at',)


class CaseAttachmentInline(admin.TabularInline):
    model = CaseAttachment
    extra = 0
    fields = ('original_filename', 'file', 'version', 'supersedes', 'uploaded_by_user')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'category', 'priority', 'owner',
                    'external_contact_name', 'needs_followup', 'last_activity_at')
    list_filter = ('status', 'category', 'priority', 'source', 'needs_followup')
    search_fields = ('title', 'summary', 'external_contact_name', 'external_contact_email')
    date_hierarchy = 'created_at'
    inlines = [CaseTaskInline, CaseReplyInline, CaseAttachmentInline]
    autocomplete_fields = ('owner', 'collaborators', 'created_by_user')
    fieldsets = (
        ('基本資訊', {'fields': ('title', 'summary', 'category', 'status', 'priority', 'source')}),
        ('客戶/聯絡人', {'fields': ('client_content_type', 'client_object_id',
                                   'external_contact_name', 'external_contact_email', 'external_contact_phone')}),
        ('內部負責', {'fields': ('owner', 'collaborators', 'created_by_user', 'created_by_external_email')}),
        ('追蹤', {'fields': ('needs_followup', 'next_followup_date', 'expected_completion_date',
                            'last_activity_at', 'closed_at')}),
    )


@admin.register(CaseTask)
class CaseTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'case', 'assignee_type', 'due_date', 'is_done', 'is_hidden')
    list_filter = ('is_done', 'is_hidden', 'assignee_type')
    search_fields = ('title', 'case__title')


@admin.register(CaseReply)
class CaseReplyAdmin(admin.ModelAdmin):
    list_display = ('case', 'author_type', 'author_display_name', 'created_at')
    list_filter = ('author_type', 'external_channel')
    search_fields = ('content', 'case__title')


@admin.register(CaseAttachment)
class CaseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'case', 'version', 'uploaded_by_user', 'created_at')
    search_fields = ('original_filename', 'case__title')


@admin.register(CaseAccessToken)
class CaseAccessTokenAdmin(admin.ModelAdmin):
    list_display = ('case', 'email', 'expires_at', 'revoked_at', 'use_count', 'last_used_at')
    list_filter = ('revoked_at',)
    search_fields = ('email', 'case__title')
    readonly_fields = ('token', 'use_count', 'last_used_at')


@admin.register(CaseNotificationPreference)
class CaseNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_on_new_reply', 'email_on_status_change', 'digest_window_minutes')


@admin.register(CaseNotificationLog)
class CaseNotificationLogAdmin(admin.ModelAdmin):
    list_display = ('case', 'event', 'channel', 'status', 'recipient_email', 'sent_at', 'created_at')
    list_filter = ('event', 'channel', 'status')
    search_fields = ('recipient_email', 'case__title')
    readonly_fields = ('case', 'event', 'channel', 'recipient_user', 'recipient_email',
                       'sent_at', 'error_message', 'created_at', 'updated_at')
