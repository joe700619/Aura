from django.db import models
from django.utils.translation import gettext_lazy as _

class ConvenienceBagLog(models.Model):
    """
    便利袋提供紀錄:
    關聯到 BookkeepingClient，紀錄每次提供便利袋的日期與數量。
    此 Model 會有 post_save 或是 save() 邏輯，
    用以更新 BookkeepingClient 的最後提供日期與最後提供數量。
    """
    client = models.ForeignKey(
        'bookkeeping.BookkeepingClient',
        on_delete=models.CASCADE,
        related_name='convenience_bag_logs',
        verbose_name=_('客戶')
    )
    date = models.DateField(_('日期'))
    quantity = models.PositiveIntegerField(_('數量'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('建立時間'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新時間'))

    class Meta:
        verbose_name = _('便利袋紀錄')
        verbose_name_plural = _('便利袋紀錄')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.client.name} - {self.date} ({self.quantity})"
