import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .progress import Progress


def get_registration_document_path(instance, filename):
    """以 owner_id_number 分桶；統編／身分證為跨案重用鍵，方便同人多家公司歸戶。"""
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    owner = instance.owner_id_number or 'unknown_owner'
    return f'registration_documents/{owner}/{new_filename}'


class RegistrationDocument(BaseModel):
    """獨立登記資料庫 — 鬆耦合的原料倉，不靠強制 FK 綁定誰。

    收料當下 Shareholder 可能還不存在（核准才投影進孤島），故以 owner_id_number
    軟鍵（統編／身分證字串）做跨案重用，而非外鍵到人主檔。progress 僅記來源案，
    刪案不傷檔。Phase 2 才會加 extracted_data。
    """

    class DocType(models.TextChoices):
        # 收料清單可勾選的型別（與 case_management.CaseTask.CollectedDocType 對齊）
        ID_CARD = 'id_card', _('身分證影本')
        NHI_CARD = 'nhi_card', _('負責人健保卡影本')
        LEASE = 'lease', _('租約或使用同意書影本')
        HOUSE_TAX = 'house_tax', _('房屋稅單或建物權狀影本')
        BANKBOOK_COVER = 'bankbook_cover', _('存摺封面影本')
        BANKBOOK_AMOUNT = 'bankbook_amount', _('存摺金額頁影本')
        BANKBOOK_TERMS = 'bankbook_terms', _('存摺約定條款影本')
        BALANCE_PROOF = 'balance_proof', _('餘額證明影本')
        FUND_SOURCE = 'fund_source', _('資金來源證明影本')
        # 倉庫專用：股東代表照（不在收料清單，由承辦上傳或以 id_number 撈用）
        PHOTO = 'photo', _('大頭照')
        # 系統產出：客戶簽署的所有權人/實質受益人聲明書 PDF（由聲明書流程投影進倉庫）
        AML_DECLARATION = 'aml_declaration', _('所有權人/實質受益人聲明書')
        # 承辦上傳、正式送件前給客戶確認的商工登記稿本（會議紀錄、股東同意書等）
        DRAFT = 'draft', _('登記稿本（待客戶確認）')
        OTHER = 'other', _('其他')

    class Source(models.TextChoices):
        CLIENT_UPLOAD = 'client_upload', _('客戶上傳')
        STAFF_UPLOAD = 'staff_upload', _('承辦上傳')

    doc_type = models.CharField(
        _('文件類型'), max_length=20, choices=DocType.choices, db_index=True
    )

    # 跨案重用軟鍵：用字串而非 FK，繞過「核准才投影 → 收料當下 Shareholder 還不存在」的時序難題
    owner_id_number = models.CharField(
        _('歸戶識別碼'), max_length=20, blank=True, db_index=True,
        help_text=_('自然人身分證或法人統編；做為同人跨案重用的軟鍵'),
    )
    owner_name = models.CharField(_('歸戶人姓名'), max_length=100, blank=True)

    # 僅記來源案，刪案不傷檔（倉庫比單一案件活得久）
    progress = models.ForeignKey(
        Progress,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='collected_documents',
        verbose_name=_('來源登記案'),
    )

    file = models.FileField(_('檔案'), upload_to=get_registration_document_path)
    original_filename = models.CharField(_('原始檔名'), max_length=255, blank=True)

    source = models.CharField(
        _('來源'), max_length=20, choices=Source.choices,
        default=Source.CLIENT_UPLOAD, db_index=True,
    )
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='uploaded_registration_documents',
        verbose_name=_('上傳人員'),
    )
    note = models.TextField(_('備註'), blank=True)

    # 換發換約留版
    supersedes = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='superseded_by',
        verbose_name=_('取代的舊版'),
    )
    version = models.PositiveIntegerField(_('版本'), default=1)

    class Meta:
        verbose_name = _('登記文件')
        verbose_name_plural = _('登記文件')
        ordering = ['-created_at']
        indexes = [
            # 同人某類文件查最新：撈倉庫重用的主要查詢
            models.Index(fields=['owner_id_number', 'doc_type']),
            models.Index(fields=['progress', 'doc_type']),
        ]

    def save(self, *args, **kwargs):
        # upload_to 會把儲存檔名改成 uuid，先在這裡留住原始檔名
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.owner_name or self.owner_id_number or '未歸戶'
        return f"{label} - {self.get_doc_type_display()}"
