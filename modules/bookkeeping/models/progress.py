import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import BaseModel
from .bookkeeping_client import BookkeepingClient

class BookkeepingSetting(BaseModel):
    """記帳進度設定 - 第一層 (靜態設定表)"""
    client = models.OneToOneField(
        BookkeepingClient, 
        on_delete=models.CASCADE, 
        related_name='bookkeeping_setting',
        verbose_name=_('客戶')
    )
    
    class Meta:
        verbose_name = _('記帳進度設定')
        verbose_name_plural = _('記帳進度設定')

    def __str__(self):
        return f"{self.client.name} - 記帳進度設定"


class BookkeepingYear(BaseModel):
    """記帳年度主表 - 第二層 (年度籃子)"""
    client = models.ForeignKey(
        BookkeepingClient, 
        on_delete=models.CASCADE, 
        related_name='bookkeeping_years',
        verbose_name=_('客戶')
    )
    year = models.PositiveIntegerField(_('年度(民國)'))
    
    class Meta:
        verbose_name = _('記帳年度')
        verbose_name_plural = _('記帳年度')
        unique_together = ('client', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"{self.client.name} - {self.year}年度"


class BookkeepingPeriod(BaseModel):
    """記帳進度明細表 - 第三層 (各期數據)"""
    year_record = models.ForeignKey(
        BookkeepingYear, 
        on_delete=models.CASCADE, 
        related_name='periods',
        verbose_name=_('所屬年度')
    )
    
    # 期別：例如 1, 3, 5, 7, 9, 11
    period_start_month = models.PositiveIntegerField(
        _('期別(起月)'),
        help_text=_('例如填寫1代表1-2月期，填寫3代表3-4月期')
    )

    class AccountStatus(models.TextChoices):
        NOT_STARTED = 'not_started', '尚未處理'
        IN_PROGRESS = 'in_progress', '處理中'
        WAITING_DOCS = 'waiting_docs', '缺憑證等待中'
        COMPLETED = 'completed', '處理完成'

    class FilingStatus(models.TextChoices):
        NOT_FILED = 'not_filed', '尚未申報'
        FILED = 'filed', '已申報'

    # -- 帳務資料 --
    account_status = models.CharField(
        _('處理進度'), max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.NOT_STARTED
    )
    accounting_date = models.DateField(
        _('完成日期'), null=True, blank=True
    )
    notes = models.TextField(
        _('備註'), blank=True, null=True
    )

    # -- 營業稅資料 --
    sales_amount = models.DecimalField(_('銷售額'), max_digits=15, decimal_places=0, default=0)
    tax_amount = models.DecimalField(_('銷項稅額'), max_digits=15, decimal_places=0, default=0)
    input_tax = models.DecimalField(_('進項稅額'), max_digits=15, decimal_places=0, default=0)
    payable_tax = models.DecimalField(_('應納(退)稅額'), max_digits=15, decimal_places=0, default=0)
    filing_status = models.CharField(
        _('申報狀態'), max_length=20,
        choices=FilingStatus.choices,
        default=FilingStatus.NOT_FILED
    )
    
    class Meta:
        verbose_name = _('記帳進度明細')
        verbose_name_plural = _('記帳進度明細')
        unique_together = ('year_record', 'period_start_month')
        ordering = ['year_record__year', 'period_start_month']

    def __str__(self):
        return f"{self.year_record} - 第 {self.period_start_month} 期"

    @property
    def period_label(self):
        """回傳 '01-02月' 這樣的字串"""
        return f"{self.period_start_month:02d}-{self.period_start_month+1:02d}月"


# ── Signals ──
@receiver(post_save, sender=BookkeepingClient)
def auto_create_bookkeeping_setting(sender, instance, created, **kwargs):
    """
    當新增 BookkeepingClient 時，自動建立其對應的 BookkeepingSetting 表。
    """
    if created:
        BookkeepingSetting.objects.get_or_create(client=instance)
