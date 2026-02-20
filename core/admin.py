from django.contrib import admin
from .models import DocumentTemplate

@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_content_type', 'uploaded_at')
    list_filter = ('model_content_type', 'uploaded_at')
    search_fields = ('name', 'description')
