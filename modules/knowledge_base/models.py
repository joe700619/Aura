from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from core.models import BaseModel


class KnowledgeEntry(BaseModel):
    """知識庫條目

    從案件問答萃取，未來可擴充為公司內部知識庫。
    embedding 由 Gemini text-embedding-004 產生（768 維）。
    """

    class Domain(models.TextChoices):
        CASE_QA = 'case_qa', '案件問答'
        REGISTRATION = 'registration', '登記業務'
        TAX_SOP = 'tax_sop', '稅務 SOP'
        GENERAL = 'general', '通用知識'

    class Category(models.TextChoices):
        TAX_FILING = 'tax_filing', '稅務申報'
        INVOICE = 'invoice', '發票管理'
        PAYROLL = 'payroll', '薪資勞健保'
        FINANCIAL = 'financial', '財務報表'
        ACCOUNTING = 'accounting', '會計處理'
        INCORPORATION = 'incorporation', '公司登記'
        INHERITANCE = 'inheritance', '遺產贈與'
        # registration 領域子分類
        INC_SETUP = 'inc_setup', '設立登記'
        INC_CHANGE = 'inc_change', '變更登記'
        INC_DISSOLVE = 'inc_dissolve', '解散/清算'
        EQUITY_TX = 'equity_tx', '股權交易'
        VAT_CHANGE = 'vat_change', '營業人變更'
        AML = 'aml', '洗錢防制'
        COMPANY_LAW_22_1 = 'company_law_22_1', '公司法 22-1'
        CAPITAL_CHANGE = 'capital_change', '增資/減資'
        MERGER = 'merger', '合併'
        SPLIT = 'split', '分割'
        OTHER_REG = 'other_reg', '其他登記'
        OTHER = 'other', '其他'

    class Visibility(models.TextChoices):
        INTERNAL = 'internal', '僅內部'
        PUBLIC = 'public', '客戶可見'

    domain = models.CharField(
        max_length=20, choices=Domain.choices,
        default=Domain.CASE_QA, verbose_name='知識領域',
        help_text='上層分流，避免不同業務的知識在檢索時混在一起'
    )

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
    source_registration = models.ForeignKey(
        'registration.CompanyFiling', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='extracted_knowledge',
        verbose_name='來源登記案'
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
            models.Index(fields=['domain', 'is_verified']),
            models.Index(fields=['domain', 'category']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.question_summary[:50]}"
