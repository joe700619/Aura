from django.contrib import admin
from django.utils import timezone

from .models import KnowledgeEntry


@admin.register(KnowledgeEntry)
class KnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ['question_summary_short', 'category', 'visibility', 'is_verified', 'embedding_status', 'created_at']
    list_filter = ['category', 'visibility', 'is_verified']
    search_fields = ['question_summary', 'answer_summary']
    readonly_fields = ['embedding_model', 'embedding_updated_at', 'verified_by', 'verified_at', 'created_at', 'updated_at']
    actions = ['verify_entries', 'generate_embeddings']

    fieldsets = (
        ('內容', {'fields': ('question_summary', 'answer_summary', 'category')}),
        ('設定', {'fields': ('visibility', 'valid_until', 'source_case', 'created_by')}),
        ('審核', {'fields': ('is_verified', 'verified_by', 'verified_at')}),
        ('Embedding', {'fields': ('embedding_model', 'embedding_updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='問題摘要')
    def question_summary_short(self, obj):
        return obj.question_summary[:60] + '...' if len(obj.question_summary) > 60 else obj.question_summary

    @admin.display(description='Embedding')
    def embedding_status(self, obj):
        return '✅' if obj.embedding is not None else '—'

    @admin.action(description='審核通過選取的條目')
    def verify_entries(self, request, queryset):
        count = queryset.filter(is_verified=False).update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now(),
        )
        self.message_user(request, f'已審核 {count} 筆條目')

    @admin.action(description='產生 Embedding（選取條目）')
    def generate_embeddings(self, request, queryset):
        from core.services.embedding import get_embedding
        count = 0
        errors = 0
        for entry in queryset:
            try:
                text = f"{entry.question_summary}\n{entry.answer_summary}"
                entry.embedding = get_embedding(text)
                entry.embedding_updated_at = timezone.now()
                entry.save(update_fields=['embedding', 'embedding_updated_at', 'updated_at'])
                count += 1
            except Exception as e:
                errors += 1
        msg = f'成功產生 {count} 筆 embedding'
        if errors:
            msg += f'，{errors} 筆失敗（請確認 GEMINI_API_KEY 設定）'
        self.message_user(request, msg)
