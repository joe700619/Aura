from django.db import models
from django.utils.translation import gettext_lazy as _

class PaymentRecord(models.Model):
    receivable = models.ForeignKey(
        'internal_accounting.Receivable', 
        related_name='payments', 
        on_delete=models.CASCADE, 
        verbose_name=_('應收帳款')
    )
    date = models.DateField(_('收款日期'))
    amount = models.DecimalField(_('金額'), max_digits=12, decimal_places=2)
    remark = models.CharField(_('備註'), max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('代收紀錄')
        verbose_name_plural = _('代收紀錄')
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.amount}"
