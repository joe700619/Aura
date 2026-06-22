"""記帳委任書（版本化範本 + 簽署實例）。

斷點落地的核心件：工商登記完成 → 客戶簽記帳委任書 → 簽署投影建記帳客戶。
見《商工登記_端到端流程架構》§11.4。

版本控制兩條紀律（普通資料庫即可，非 Git）：
  ①範本不就地改：改條款＝在 EngagementLetterTemplate 新增一列版本，舊版永遠查得到。
  ②簽署即凍結：EngagementLetter 簽成那刻把當下渲染內容存進 rendered_snapshot，
    絕不用「當前範本」事後重生（否則改範本會竄改歷史簽署內容）。

委任書是網頁版＋按同意（不像 AML 聲明書要手寫簽名）。
"""
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

from .billing import ServiceFee
from .bookkeeping_client import BookkeepingClient


class EngagementLetterTemplate(BaseModel):
    """記帳委任書範本（版本列）。改條款＝新增一列、不就地改；唯一 active 供新委任書取用。"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        ACTIVE = 'active', '使用中'
        ARCHIVED = 'archived', '已封存'

    version = models.PositiveIntegerField(_('版本'), unique=True, editable=False)
    title = models.CharField(_('範本名稱'), max_length=200, default='記帳服務委任書')
    body_html = models.TextField(
        _('條款本文'),
        help_text=_('支援 Django Template 佔位符：{{ company_name }} {{ tax_id }} '
                    '{{ engagement_start_date }} {{ service_fee }} {{ billing_cycle }} {{ fee_note }}'),
    )
    status = models.CharField(
        _('狀態'), max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
    )
    effective_from = models.DateField(_('生效日'), blank=True, null=True)
    notes = models.TextField(_('版本備註'), blank=True, help_text=_('這版改了什麼'))

    class Meta:
        verbose_name = _('記帳委任書範本')
        verbose_name_plural = _('記帳委任書範本')
        ordering = ['-version']

    def __str__(self):
        return f"記帳委任書 v{self.version}（{self.get_status_display()}）"

    def save(self, *args, **kwargs):
        # 版本號自動遞增（建立時）。
        if not self.version:
            last = EngagementLetterTemplate.objects.order_by('-version').first()
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)
        # 唯一 active：設為使用中時，其他版自動封存。
        if self.status == self.Status.ACTIVE:
            EngagementLetterTemplate.objects.exclude(pk=self.pk).filter(
                status=self.Status.ACTIVE
            ).update(status=self.Status.ARCHIVED)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(status=cls.Status.ACTIVE).order_by('-version').first()


class EngagementLetter(BaseModel):
    """記帳委任書簽署實例。簽署成立＝投影建 BookkeepingClient + ServiceFee。"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        SENT = 'sent', '已寄出待簽'
        SIGNED = 'signed', '已簽署'
        DECLINED = 'declined', '已婉拒'

    class PricingType(models.TextChoices):
        BASE = 'base', '基礎方案'
        CUSTOM = 'custom', '客製'

    class FirmName(models.TextChoices):
        """受任事務所主體。會計師事務所與記帳士事務所是兩個不同主體，
        切換時整份委任書（信頭、受任人、頁尾）一併套用。"""
        CPA = 'cpa', '勤信聯合會計師事務所'
        BOOKKEEPER = 'bookkeeper', '勤信聯合記帳士事務所'

    # ── 來源連結（皆可空，string ref 跨模組）──
    inquiry = models.ForeignKey(
        'case_management.Inquiry', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='engagement_letters',
        verbose_name=_('來源諮詢'),
    )
    progress_no = models.CharField(
        _('來源工商案號'), max_length=50, blank=True,
        help_text=_('對應 registration.Progress.registration_no（軟連結）'),
    )

    # ── 簽署投影建客戶用的公司資料快照 ──
    company_name = models.CharField(_('公司名稱'), max_length=100)
    tax_id = models.CharField(_('統一編號'), max_length=20, blank=True)
    contact_name = models.CharField(_('聯絡人'), max_length=50, blank=True)
    contact_email = models.EmailField(_('Email'), blank=True)
    contact_phone = models.CharField(_('電話'), max_length=20, blank=True)
    client_source = models.CharField(
        _('客戶來源'), max_length=20,
        choices=BookkeepingClient.ClientSource.choices,
        default=BookkeepingClient.ClientSource.OUR_FIRM,
    )
    firm_name = models.CharField(
        _('受任事務所'), max_length=20,
        choices=FirmName.choices, default=FirmName.CPA,
        help_text=_('委任書信頭、受任人、頁尾顯示的事務所主體'),
    )

    # ── 委任內容 ──
    engagement_start_date = models.DateField(
        _('開始委任日期'), blank=True, null=True,
        help_text=_('人工填；配合營業稅週期，通常從最近要申報的營業稅期起算。'
                    '結案自動產生的草稿此欄為空，發送前須補填'),
    )
    pricing_type = models.CharField(
        _('收費方案'), max_length=20, choices=PricingType.choices,
        default=PricingType.BASE,
    )
    service_fee = models.IntegerField(_('每月服務費'), default=0)
    ledger_fee = models.IntegerField(_('帳簿費'), default=0)
    billing_cycle = models.CharField(
        _('收費週期'), max_length=30,
        choices=ServiceFee.BillingCycle.choices,
        default=ServiceFee.BillingCycle.BIMONTHLY,
    )
    fee_note = models.TextField(
        _('費用說明'), blank=True,
        help_text=_('客製方案請說明複雜度原因（如發票量大、兼營、外幣帳）'),
    )

    # ── 版本與快照 ──
    template_version = models.ForeignKey(
        EngagementLetterTemplate, on_delete=models.PROTECT,
        related_name='letters', verbose_name=_('採用範本版本'),
    )
    rendered_snapshot = models.TextField(
        _('簽署凍結內容'), blank=True,
        help_text=_('簽署那刻渲染並凍結，永不重生'),
    )

    # ── 簽署 token 流 ──
    token = models.UUIDField(_('簽署 Token'), default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        _('狀態'), max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
    )
    sent_at = models.DateTimeField(_('寄出時間'), blank=True, null=True)
    signed_at = models.DateTimeField(_('簽署時間'), blank=True, null=True)
    signer_ip = models.GenericIPAddressField(_('簽署 IP'), blank=True, null=True)
    decline_reason = models.TextField(_('婉拒原因'), blank=True)

    # ── 投影產物（idempotency 護欄）──
    created_client = models.ForeignKey(
        'bookkeeping.BookkeepingClient', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='source_engagement_letters',
        verbose_name=_('已建立的記帳客戶'),
    )

    class Meta:
        verbose_name = _('記帳委任書')
        verbose_name_plural = _('記帳委任書')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.company_name} 記帳委任書（{self.get_status_display()}）"

    @property
    def is_signable(self):
        return self.status in (self.Status.SENT, self.Status.DRAFT)

    @property
    def firm_name_en(self):
        """信頭英文副標，隨受任事務所切換。"""
        return ('Chi-Xin United CPAs'
                if self.firm_name == self.FirmName.CPA
                else 'Chi-Xin United Certified Public Bookkeepers')

    # ── 供 public_v2 範本使用的語意別名（對應現有欄位，零 migration）──
    @property
    def agreed_at(self):
        """已同意時間＝簽署時間（範本以此判斷『已確認』狀態並顯示時間）。"""
        return self.signed_at

    @property
    def declined_at(self):
        """已婉拒時間（範本僅作布林判斷用；無專屬欄位，婉拒時以 updated_at 近似）。"""
        return self.updated_at if self.status == self.Status.DECLINED else None
