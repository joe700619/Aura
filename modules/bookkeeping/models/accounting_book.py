from django.db import models
from django.utils.translation import gettext_lazy as _

class AccountingBookLog(models.Model):
    """
    帳冊管理紀錄:
    關聯到 BookkeepingClient，紀錄每一年度的帳冊、光碟、發票、與簽收單等資訊。
    """
    client = models.ForeignKey(
        'bookkeeping.BookkeepingClient',
        on_delete=models.CASCADE,
        related_name='accounting_book_logs',
        verbose_name=_('客戶')
    )
    date = models.DateField(_('日期'))
    year = models.CharField(_('年度'), max_length=10)
    cd_rom = models.CharField(_('光碟'), max_length=50, blank=True)
    sales_invoice_qty = models.PositiveIntegerField(_('銷項發票數量'), default=0)
    receipt_form = models.FileField(
        _('簽收單'), 
        upload_to='bookkeeping_receipts/%Y/%m/',
        blank=True, null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('建立時間'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新時間'))

    class Meta:
        verbose_name = _('帳冊紀錄')
        verbose_name_plural = _('帳冊紀錄')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.client.name} - {self.year} 帳冊"
