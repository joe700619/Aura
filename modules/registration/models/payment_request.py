import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ProgressPaymentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   _('待付款')
        PAID      = 'paid',      _('已付款')
        CANCELLED = 'cancelled', _('已取消')

    PICKUP_CHOICES = [
        ('mail', _('郵寄')),
        ('self', _('自取')),
    ]

    progress = models.ForeignKey(
        'registration.Progress',
        on_delete=models.CASCADE,
        related_name='payment_requests',
        verbose_name=_('登記進度'),
    )
    token = models.UUIDField(_('支付 Token'), default=uuid.uuid4, unique=True, editable=False)
    amount = models.PositiveIntegerField(_('請款金額'))
    description = models.CharField(_('說明'), max_length=100, blank=True, help_text=_('例如：頭期款、尾款'))
    status = models.CharField(
        _('狀態'), max_length=20,
        choices=Status.choices, default=Status.PENDING,
    )

    # 由客戶在公開付款頁面填寫
    recipient_name  = models.CharField(_('收件人姓名'), max_length=100, blank=True)
    recipient_phone = models.CharField(_('收件人電話'), max_length=50, blank=True)
    recipient_addr  = models.CharField(_('收件地址'), max_length=255, blank=True)
    pickup_method   = models.CharField(_('取件方式'), max_length=20, choices=PICKUP_CHOICES, default='mail')

    created_at = models.DateTimeField(_('建立時間'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新時間'), auto_now=True)

    class Meta:
        verbose_name = _('付款請求')
        verbose_name_plural = _('付款請求')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.progress.registration_no} - {self.description or '付款'} ${self.amount} ({self.get_status_display()})"
