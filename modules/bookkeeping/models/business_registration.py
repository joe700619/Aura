import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import BaseModel
from .bookkeeping_client import BookkeepingClient


def get_business_registration_document_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    tax_id = instance.registration.client.tax_id or 'unknown_client'
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
    """商工登記文件（inline）— 日期、名稱、檔案。"""
    registration = models.ForeignKey(
        BusinessRegistration,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('所屬商工登記'),
    )
    document_date = models.DateField(_('日期'), null=True, blank=True)
    name = models.CharField(_('名稱'), max_length=255)
    file = models.FileField(
        _('檔案'),
        upload_to=get_business_registration_document_path,
        blank=True, null=True,
    )

    class Meta:
        verbose_name = _('商工登記文件')
        verbose_name_plural = _('商工登記文件')
        ordering = ['-document_date', '-created_at']

    def __str__(self):
        return f"{self.registration.client.name} - {self.name}"


@receiver(post_save, sender=BookkeepingClient)
def auto_create_business_registration(sender, instance, created, **kwargs):
    """新增 BookkeepingClient 時，自動建立 BusinessRegistration"""
    if created:
        BusinessRegistration.objects.get_or_create(client=instance)
