from django.db import models
from django.utils.translation import gettext_lazy as _


class ReceivableNotification(models.Model):
    class Channel(models.TextChoices):
        LINE = 'LINE', _('Line')
        EMAIL = 'EMAIL', _('Email')

    receivable = models.ForeignKey(
        'internal_accounting.Receivable',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('應收帳款')
    )
    threshold_days = models.IntegerField(_('逾期閾值天數'))   # 30 / 40 / 50 / 60
    channel = models.CharField(_('通知管道'), max_length=10, choices=Channel.choices)
    sent_at = models.DateTimeField(_('發送時間'), auto_now_add=True)
    success = models.BooleanField(_('是否成功'), default=True)
    error_message = models.TextField(_('錯誤訊息'), blank=True)

    class Meta:
        verbose_name = _('逾期通知紀錄')
        verbose_name_plural = _('逾期通知紀錄')
        unique_together = ('receivable', 'threshold_days', 'channel')
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.receivable} - {self.threshold_days}天 - {self.channel}"
