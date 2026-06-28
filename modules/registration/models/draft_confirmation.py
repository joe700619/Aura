import os
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .progress import Progress
from .registration_document import RegistrationDocument


def get_draft_signature_path(instance, filename):
    ext = os.path.splitext(filename)[1] or '.png'
    return f'draft_confirmation_signatures/{uuid.uuid4().hex}{ext}'


class DraftConfirmation(BaseModel):
    """商工登記稿本確認：正式送件前，把承辦上傳的稿本下發給客戶線上校對 + 手寫簽名確認。

    觸發時機：承辦在進度表「稿本確認」工作台上傳稿本後產生一筆，透過 LINE/Email 把
    token 連結給客戶。客戶免登入「唯讀檢視/下載」稿本 → 手寫簽名 → 簽署即凍結快照
    （鎖住確認了哪幾份文件 + 簽名圖 + 留痕）。

    規則：
    - 一個 Progress 同時只允許一筆 active（status=sent）；重發或重傳新稿本時舊筆自動轉 voided。
    - 連結預設 7 天到期，過期只能由承辦重發（不展延）。
    - 簽署即凍結，不事後用當前稿本/文字重生（所見即所簽）。
    - 用印授權為選配：承辦勾選後客戶頁多顯示一段授權條款，文字於發送當下凍進快照。
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', _('草稿')
        SENT = 'sent', _('已寄送')
        CONFIRMED = 'confirmed', _('已確認')
        VOIDED = 'voided', _('已作廢')

    token = models.UUIDField(_('確認 Token'), default=uuid.uuid4, unique=True, editable=False)

    # 同 module FK，主檔刪則確認紀錄跟著刪（稿本確認附屬於單一登記案）
    progress = models.ForeignKey(
        Progress,
        on_delete=models.CASCADE,
        related_name='draft_confirmations',
        verbose_name=_('登記案'),
    )
    status = models.CharField(
        _('狀態'), max_length=20, choices=Status.choices,
        default=Status.SENT, db_index=True,
    )

    # 要客戶確認的稿本：發送當下凍結這份清單（檔案本身因 R2 不覆寫 + UUID 檔名而不可變）
    documents = models.ManyToManyField(
        RegistrationDocument,
        related_name='draft_confirmations',
        blank=True,
        verbose_name=_('稿本文件'),
    )

    # 用印授權
    seal_authorization = models.BooleanField(_('包含用印授權'), default=False)
    authorization_text_snapshot = models.TextField(
        _('用印授權文字快照'), blank=True,
        help_text=_('發送當下凍結客戶將看到的授權文字，標準文字改版不影響舊紀錄'),
    )
    seal_authorized = models.BooleanField(_('客戶已授權用印'), default=False)

    # 發送留痕
    sent_at = models.DateTimeField(_('寄送時間'), null=True, blank=True)
    expires_at = models.DateTimeField(_('連結到期時間'), null=True, blank=True)
    recipient_email = models.EmailField(_('寄送 Email'), blank=True)
    recipient_line_id = models.CharField(_('寄送 LINE/Room ID'), max_length=100, blank=True)

    # 簽署留痕 + 快照
    signature_image = models.ImageField(
        _('客戶手寫簽名'), upload_to=get_draft_signature_path, blank=True,
    )
    signed_at = models.DateTimeField(_('確認時間'), null=True, blank=True, db_index=True)
    signer_name = models.CharField(_('簽署人姓名'), max_length=100, blank=True)
    signer_email = models.EmailField(_('簽署人 Email'), blank=True)
    signer_line_id = models.CharField(_('簽署人 LINE/Room ID'), max_length=100, blank=True)
    signer_ip = models.GenericIPAddressField(_('簽署來源 IP'), null=True, blank=True)

    class Meta:
        verbose_name = _('稿本確認')
        verbose_name_plural = _('稿本確認')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['progress', 'status']),
        ]

    def __str__(self):
        return f"{self.progress.company_name} 稿本確認 ({self.get_status_display()})"

    @property
    def is_expired(self):
        return bool(
            self.status == self.Status.SENT
            and self.expires_at
            and timezone.now() > self.expires_at
        )

    @property
    def is_signable(self):
        """客戶端可簽：已寄送且未過期。"""
        return self.status == self.Status.SENT and not self.is_expired
