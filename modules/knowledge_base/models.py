from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from core.models import BaseModel


class KnowledgeEntry(BaseModel):
    """知識庫條目

    從案件問答萃取，未來可擴充為公司內部知識庫。
    embedding 由 Gemini text-embedding-004 產生（768 維）。
    """

    class Category(models.TextChoices):
        TAX_FILING = 'tax_filing', '稅務申報'
        INVOICE = 'invoice', '發票管理'
        PAYROLL = 'payroll', '薪資勞健保'
        FINANCIAL = 'financial', '財務報表'
        ACCOUNTING = 'accounting', '會計處理'
        INCORPORATION = 'incorporation', '公司登記'
        INHERITANCE = 'inheritance', '遺產贈與'
        OTHER = 'other', '其他'

    class Visibility(models.TextChoices):
        INTERNAL = 'internal', '僅內部'
        PUBLIC = 'public', '客戶可見'

    question_summary = models.TextField(verbose_name='問題摘要')
    answer_summary = models.TextField(verbose_name='回答摘要')
    checklist = models.TextField(blank=True, verbose_name='準備清單', help_text='每行一個項目')
    category = models.CharField(
        max_length=20, choices=Category.choices,
        default=Category.OTHER, verbose_name='類別'
    )

    embedding = VectorField(dimensions=768, null=True, blank=True, verbose_name='向量')
    embedding_model = models.CharField(max_length=100, blank=True, default='text-embedding-004')
    embedding_updated_at = models.DateTimeField(null=True, blank=True)

    visibility = models.CharField(
        max_length=10, choices=Visibility.choices,
        default=Visibility.INTERNAL, verbose_name='可見範圍'
    )
    valid_until = models.DateField(null=True, blank=True, verbose_name='有效期限')

    is_verified = models.BooleanField(default=False, verbose_name='已審核')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_knowledge',
        verbose_name='審核者'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    source_case = models.ForeignKey(
        'case_management.Case', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='extracted_knowledge',
        verbose_name='來源案件'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_knowledge',
        verbose_name='建立者'
    )

    class Meta:
        verbose_name = '知識條目'
        verbose_name_plural = '知識條目'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_verified']),
            models.Index(fields=['visibility', 'is_verified']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.question_summary[:50]}"
