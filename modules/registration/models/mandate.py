"""公司登記委任書（版本化範本 + 簽署實例）。

設計沿兩條既有路線混成：
  ①簽署骨架（token 免登入 / 手寫簽名 / LINE+Email / 7 天到期 / 作廢重發）
    照 DraftConfirmation（見 draft_confirmation.py）。
  ②內容產生（版本化範本 + 佔位符渲染 + 快照凍結）
    照 bookkeeping.EngagementLetterTemplate 的兩條紀律：
    範本不就地改（改條款＝新增一列版本）、內容一經凍結永不重生。

與記帳委任書的差異：凍結時點在「發送」而非「簽署」——委任書內容含進度表的
報價單資料，發送當下把渲染結果 + 報價明細一併凍進快照，之後改報價不影響已
寄出的連結（所見即所簽）；報價有變由承辦重發（舊單自動 voided）。
"""
import os
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .progress import Progress


def get_mandate_signature_path(instance, filename):
    ext = os.path.splitext(filename)[1] or '.png'
    return f'registration_mandate_signatures/{uuid.uuid4().hex}{ext}'


class RegistrationMandateTemplate(BaseModel):
    """公司登記委任書範本（版本列）。改條款＝新增一列、不就地改；唯一 active 供發送時取用。"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('草稿')
        ACTIVE = 'active', _('使用中')
        ARCHIVED = 'archived', _('已封存')

    version = models.PositiveIntegerField(_('版本'), unique=True, editable=False)
    title = models.CharField(_('範本名稱'), max_length=200, default='公司登記委任書')
    body_html = models.TextField(
        _('條款本文'),
        help_text=_('支援 Django Template 佔位符：{{ company_name }} {{ unified_business_no }} '
                    '{{ main_contact }} {{ acceptance_date }} {{ case_types }} '
                    '{{ service_fee_total }} {{ advance_total }} {{ pre_collection_total }} '
                    '{{ uncollected_total }} {{ today }}。'
                    '報價明細表由客戶頁固定版位顯示，不必寫在本文。'),
    )
    status = models.CharField(
        _('狀態'), max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
    )
    effective_from = models.DateField(_('生效日'), blank=True, null=True)
    notes = models.TextField(_('版本備註'), blank=True, help_text=_('這版改了什麼'))

    class Meta:
        verbose_name = _('登記委任書範本')
        verbose_name_plural = _('登記委任書範本')
        ordering = ['-version']

    def __str__(self):
        return f"登記委任書 v{self.version}（{self.get_status_display()}）"

    def save(self, *args, **kwargs):
        # 版本號自動遞增（建立時）。
        if not self.version:
            last = RegistrationMandateTemplate.objects.order_by('-version').first()
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)
        # 唯一 active：設為使用中時，其他版自動封存。
        if self.status == self.Status.ACTIVE:
            RegistrationMandateTemplate.objects.exclude(pk=self.pk).filter(
                status=self.Status.ACTIVE
            ).update(status=self.Status.ARCHIVED)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(status=cls.Status.ACTIVE).order_by('-version').first()


class RegistrationMandate(BaseModel):
    """公司登記委任書簽署實例。

    觸發時機：承辦在進度表「委任書」工作台按發送 → 建一筆（status=sent）並凍結
    快照，透過 LINE/Email 把 token 連結給客戶。客戶免登入閱覽 → 手寫簽名（或婉拒）。

    規則：
    - 一個 Progress 同時只允許一筆 active（status=sent）；重發時舊筆自動轉 voided。
    - 連結預設 7 天到期，過期只能由承辦重發（不展延）。
    - 內容於發送當下凍結（rendered_snapshot + quotation_snapshot），不事後重生。
    - 簽署/婉拒由 service 同步回寫 Progress.mandate_return（簽核中/核准/拒絕）。
    """

    class Status(models.TextChoices):
        SENT = 'sent', _('已寄送')
        SIGNED = 'signed', _('已簽署')
        DECLINED = 'declined', _('已婉拒')
        VOIDED = 'voided', _('已作廢')

    token = models.UUIDField(_('簽署 Token'), default=uuid.uuid4, unique=True, editable=False)

    # 同 module FK，主檔刪則委任書跟著刪（委任書附屬於單一登記案；Progress 本身走軟刪）
    progress = models.ForeignKey(
        Progress,
        on_delete=models.CASCADE,
        related_name='mandates',
        verbose_name=_('登記案'),
    )
    status = models.CharField(
        _('狀態'), max_length=20, choices=Status.choices,
        default=Status.SENT, db_index=True,
    )

    # 版本與快照（發送當下凍結）
    template_version = models.ForeignKey(
        RegistrationMandateTemplate, on_delete=models.PROTECT,
        related_name='mandates', verbose_name=_('採用範本版本'),
    )
    rendered_snapshot = models.TextField(
        _('條款凍結內容'), blank=True,
        help_text=_('發送當下渲染並凍結，永不重生'),
    )
    quotation_snapshot = models.JSONField(
        _('報價明細快照'), default=dict, blank=True,
        help_text=_('發送當下凍結的報價單明細與合計，之後改報價不影響本紀錄'),
    )

    # 發送留痕
    sent_at = models.DateTimeField(_('寄送時間'), null=True, blank=True)
    expires_at = models.DateTimeField(_('連結到期時間'), null=True, blank=True)
    recipient_email = models.EmailField(_('寄送 Email'), blank=True)
    recipient_line_id = models.CharField(_('寄送 LINE/Room ID'), max_length=100, blank=True)

    # 簽署留痕
    signature_image = models.ImageField(
        _('客戶手寫簽名'), upload_to=get_mandate_signature_path, blank=True,
    )
    signed_at = models.DateTimeField(_('簽署時間'), null=True, blank=True, db_index=True)
    signer_name = models.CharField(_('簽署人姓名'), max_length=100, blank=True)
    signer_email = models.EmailField(_('簽署人 Email'), blank=True)
    signer_line_id = models.CharField(_('簽署人 LINE/Room ID'), max_length=100, blank=True)
    signer_ip = models.GenericIPAddressField(_('簽署來源 IP'), null=True, blank=True)

    # 婉拒留痕
    declined_at = models.DateTimeField(_('婉拒時間'), null=True, blank=True)
    decline_reason = models.TextField(_('婉拒原因'), blank=True)

    class Meta:
        verbose_name = _('登記委任書')
        verbose_name_plural = _('登記委任書')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['progress', 'status']),
        ]

    def __str__(self):
        return f"{self.progress.company_name} 登記委任書（{self.get_status_display()}）"

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
