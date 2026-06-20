import os
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .progress import Progress
from .registration_document import RegistrationDocument


def get_bo_signature_path(instance, filename):
    ext = os.path.splitext(filename)[1] or '.png'
    return f'bo_declaration_signatures/{uuid.uuid4().hex}{ext}'


class BeneficialOwnerDeclaration(BaseModel):
    """所有權人或實質受益人聲明書（法人適用）的簽署紀錄。

    客戶在免登入頁校對填空欄位 + 手寫簽名後產生：本表保存結構化欄位、手寫簽名圖、
    與簽署留痕（email/IP/時間）；簽好的 PDF 投影成一筆 RegistrationDocument
    （doc_type=aml_declaration）落入獨立登記資料庫，並由 rendered_document 回指。
    簽署即凍結，不事後用當前範本重生。
    """

    progress = models.ForeignKey(
        Progress,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bo_declarations',
        verbose_name=_('來源登記案'),
    )

    company_name = models.CharField(_('本法人名稱'), max_length=255)
    transaction_description = models.CharField(_('所從事之交易'), max_length=255, blank=True)
    representative_title = models.CharField(_('代表人職稱'), max_length=100)

    representative_signature = models.ImageField(
        _('代表人手寫簽名'), upload_to=get_bo_signature_path,
    )

    signed_at = models.DateTimeField(_('簽署時間'), db_index=True)
    signer_email = models.EmailField(_('簽署人 Email'), blank=True)
    signer_ip = models.GenericIPAddressField(_('簽署來源 IP'), null=True, blank=True)

    rendered_document = models.ForeignKey(
        RegistrationDocument,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name=_('簽好的聲明書 PDF'),
    )

    class Meta:
        verbose_name = _('實質受益人聲明書')
        verbose_name_plural = _('實質受益人聲明書')
        ordering = ['-signed_at']
        indexes = [
            models.Index(fields=['progress', '-signed_at']),
        ]

    def __str__(self):
        return f"{self.company_name} 聲明書 ({self.signed_at:%Y-%m-%d})"
