import os
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


def get_id_card_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or '.jpg'
    return f'shareholder_id_cards/{uuid.uuid4().hex}{ext}'


class Shareholder(BaseModel):
    class Nationality(models.TextChoices):
        TW = 'TW', _('中華民國')
        CN = 'CN', _('中國大陸')
        HK = 'HK', _('香港')
        KR = 'KR', _('韓國')

    name = models.CharField(_('姓名'), max_length=100)
    id_number = models.CharField(_('身分證字號'), max_length=20, unique=True)
    foreign_tax_id = models.CharField(_('國稅局外國人證件號碼'), max_length=30, blank=True, null=True)
    nationality = models.CharField(_('國籍'), max_length=2, choices=Nationality.choices, default=Nationality.TW)
    birthday = models.DateField(_('生日'), null=True, blank=True)
    address = models.CharField(_('地址'), max_length=255, blank=True, null=True)
    is_active = models.BooleanField(_('狀態'), default=True, choices=[(True, '使用中'), (False, '未使用')])
    id_card_front = models.ImageField(_('身分證正面'), upload_to=get_id_card_path, blank=True, null=True)
    id_card_back = models.ImageField(_('身分證背面'), upload_to=get_id_card_path, blank=True, null=True)
    note = models.TextField(_('備註'), blank=True, null=True)

    class Meta:
        verbose_name = _('股東及董監事')
        verbose_name_plural = _('股東及董監事')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.id_number})"
