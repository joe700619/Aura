from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.models import BaseModel


class PreCollection(BaseModel):
    class Status(models.TextChoices):
        UNMATCHED = 'unmatched', _('未核銷')
        MATCHED   = 'matched',   _('已核銷')

    pre_collection_no = models.CharField(
        _('預收單號'), max_length=50, unique=True, blank=True
    )
    date = models.DateField(_('收款日期'), default=timezone.now)
    company_name = models.CharField(_('公司名稱'), max_length=255)
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, null=True)
    amount = models.DecimalField(_('預收金額'), max_digits=12, decimal_places=0, default=0)
    METHOD_CHOICES = [
        ('ecpay', _('綠界')),
        ('bank',  _('銀行存款')),
        ('cash',  _('現金')),
        ('other', _('其他')),
    ]
    method = models.CharField(_('收款方式'), max_length=20, choices=METHOD_CHOICES, default='ecpay')
    transaction_no = models.CharField(
        _('交易編號'), max_length=100, blank=True, null=True,
        help_text=_('綠界 merchant_trade_no')
    )
    remarks = models.TextField(_('備註'), blank=True)

    # 來源（GenericFK → Progress）
    source_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('來源類型')
    )
    source_id = models.PositiveIntegerField(_('來源 ID'), null=True, blank=True)
    source_object = GenericForeignKey('source_content_type', 'source_id')

    # 核銷後關聯
    status = models.CharField(
        _('狀態'), max_length=20,
        choices=Status.choices, default=Status.UNMATCHED
    )
    matched_receivable = models.ForeignKey(
        'internal_accounting.Receivable',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pre_collections',
        verbose_name=_('核銷應收帳款')
    )
    matched_collection = models.OneToOneField(
        'internal_accounting.Collection',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pre_collection',
        verbose_name=_('核銷收款單')
    )

    class Meta:
        verbose_name = _('預收款項')
        verbose_name_plural = _('預收款項')
        ordering = ['-date', '-pre_collection_no']

    def __str__(self):
        return f"{self.pre_collection_no or 'No No'} - {self.company_name} ${self.amount}"

    def save(self, *args, **kwargs):
        if not self.pre_collection_no:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"PC{today_str}"
            last = PreCollection.objects.filter(
                pre_collection_no__startswith=prefix
            ).order_by('-pre_collection_no').first()
            if last:
                try:
                    seq = int(last.pre_collection_no.replace(prefix, '')) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.pre_collection_no = f"{prefix}{seq:03d}"
        super().save(*args, **kwargs)
