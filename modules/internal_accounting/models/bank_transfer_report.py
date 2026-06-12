from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class BankTransferReport(BaseModel):
    """客戶端「銀行匯款回報」。

    客戶在 client_portal 自行回報「我已匯款，後五碼是 XXXXX」，
    此為**待核對**紀錄，不直接影響應收餘額。
    會計在後台核對銀行對帳單後，確認 → 自動產生對應的 Collection（真實入帳）。
    """

    class Status(models.TextChoices):
        PENDING   = 'pending',   _('待核對')
        CONFIRMED = 'confirmed', _('已確認')
        REJECTED  = 'rejected',  _('不符')

    receivable = models.ForeignKey(
        'internal_accounting.Receivable',
        on_delete=models.CASCADE,
        related_name='transfer_reports',
        verbose_name=_('應收帳款'),
        db_index=True,
    )
    last_five_digits = models.CharField(_('匯款帳號後五碼'), max_length=5)
    transfer_date = models.DateField(_('匯款日期'))
    amount = models.DecimalField(_('匯款金額'), max_digits=12, decimal_places=0, default=0)

    status = models.CharField(
        _('核對狀態'), max_length=20,
        choices=Status.choices, default=Status.PENDING, db_index=True,
    )
    collection = models.ForeignKey(
        'internal_accounting.Collection',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transfer_reports',
        verbose_name=_('確認後產生的收款單'),
    )
    remarks = models.TextField(_('備註'), blank=True)

    class Meta:
        verbose_name = _('銀行匯款回報')
        verbose_name_plural = _('銀行匯款回報')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.receivable.receivable_no or self.receivable_id} - 後五碼 {self.last_five_digits} ({self.get_status_display()})"
