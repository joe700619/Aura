from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel

class Collection(BaseModel):
    METHOD_CHOICES = [
        ('bank', _('銀行存款')),
        ('ecpay', _('綠界')),
        ('cash', _('現金')),
        ('bad_debt', _('壞帳或折讓')),
        ('other', _('其他')),
    ]

    receivable = models.ForeignKey(
        'internal_accounting.Receivable',
        on_delete=models.CASCADE,
        related_name='collections',
        verbose_name=_('應收帳款')
    )
    collection_no = models.CharField(_('收款單號'), max_length=50, unique=True, blank=True)
    date = models.DateField(_('收款日期'), default=timezone.now)
    method = models.CharField(_('收款方式'), max_length=20, choices=METHOD_CHOICES, default='bank')
    
    amount = models.DecimalField(_('收款金額'), max_digits=12, decimal_places=0, default=0)
    tax = models.DecimalField(_('扣繳稅款'), max_digits=12, decimal_places=0, default=0)
    fee = models.DecimalField(_('手續費'), max_digits=12, decimal_places=0, default=0)
    allowance = models.DecimalField(_('壞帳或折讓'), max_digits=12, decimal_places=0, default=0)
    total = models.DecimalField(_('收款合計'), max_digits=12, decimal_places=0, default=0)
    
    voucher = models.ForeignKey(
        'internal_accounting.Voucher',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='collections',
        verbose_name=_('對應傳票')
    )
    is_correction_needed = models.BooleanField(_('是否需補扣'), default=False)
    auto_created = models.BooleanField(_('系統自動建立'), default=False, help_text=_('綠界付款後由系統自動產生'))
    reporting_amount = models.DecimalField(_('扣繳申報金額'), max_digits=12, decimal_places=0, default=0)
    is_posted = models.BooleanField(_('已過帳'), default=False)
    
    remarks = models.TextField(_('備註'), blank=True)

    class Meta:
        verbose_name = _('收款管理')
        verbose_name_plural = _('收款管理')
        ordering = ['-date', '-collection_no']

    def __str__(self):
        return self.collection_no or f"Collection {self.pk}"

    def save(self, *args, **kwargs):
        # Coerce all monetary fields to integers (strip decimals from external transfers)
        self.amount = Decimal(str(self.amount)).quantize(Decimal('1'))
        self.tax = Decimal(str(self.tax)).quantize(Decimal('1'))
        self.fee = Decimal(str(self.fee)).quantize(Decimal('1'))
        self.allowance = Decimal(str(self.allowance)).quantize(Decimal('1'))

        # Calculate total
        self.total = self.amount + self.tax + self.fee + self.allowance
        
        # Generate collection_no if not present
        if not self.collection_no:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"CO{today_str}"
            
            last_collection = Collection.objects.filter(collection_no__startswith=prefix).order_by('-collection_no').first()
            if last_collection:
                last_no = int(last_collection.collection_no[-3:])
                new_no = last_no + 1
            else:
                new_no = 1
            
            self.collection_no = f"{prefix}{new_no:03d}"
            
        super().save(*args, **kwargs)
