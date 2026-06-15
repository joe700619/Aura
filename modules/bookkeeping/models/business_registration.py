import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .bookkeeping_client import BookkeepingClient


def get_business_registration_document_path(instance, filename):
    # 保留供舊 migration (0041) import；新檔案請用 get_business_registration_file_path
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    tax_id = instance.registration.client.tax_id or 'unknown_client'
    return f'business_registration/documents/{tax_id}/{new_filename}'


def get_business_registration_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    tax_id = instance.document.registration.client.tax_id or 'unknown_client'
    return f'business_registration/documents/{tax_id}/{new_filename}'


class BusinessRegistration(BaseModel):
    """商工登記 — 一個記帳客戶對應一筆，無年度區分。"""
    client = models.OneToOneField(
        BookkeepingClient,
        on_delete=models.CASCADE,
        related_name='business_registration',
        verbose_name=_('客戶'),
    )

    class Meta:
        verbose_name = _('商工登記')
        verbose_name_plural = _('商工登記')

    def __str__(self):
        return f"{self.client.name} - 商工登記"


class BusinessRegistrationDocument(BaseModel):
    """商工登記文件事件（inline）— 一個日期事件，底下可掛多份檔案。"""
    registration = models.ForeignKey(
        BusinessRegistration,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('所屬商工登記'),
    )
    document_date = models.DateField(_('日期'), null=True, blank=True)
    name = models.CharField(_('名稱'), max_length=255)

    class Meta:
        verbose_name = _('商工登記文件')
        verbose_name_plural = _('商工登記文件')
        ordering = ['-document_date', '-created_at']

    def __str__(self):
        return f"{self.registration.client.name} - {self.name}"


class BusinessRegistrationDocumentFile(BaseModel):
    """商工登記文件的檔案 — 一個事件可掛多份；保留上傳時的原始檔名。"""
    document = models.ForeignKey(
        BusinessRegistrationDocument,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_('所屬文件事件'),
    )
    file = models.FileField(
        _('檔案'),
        upload_to=get_business_registration_file_path,
    )
    original_filename = models.CharField(_('原始檔名'), max_length=255, blank=True)

    class Meta:
        verbose_name = _('商工登記檔案')
        verbose_name_plural = _('商工登記檔案')
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        # upload_to 會把儲存檔名改成 uuid，先在這裡留住原始檔名
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_filename or os.path.basename(self.file.name)


# Signal 已集中到 modules/bookkeeping/models/signals.py
