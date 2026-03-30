from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import BaseModel


class ServiceFee(BaseModel):
    """
    服務費用定義 - 記錄跟該客戶收費的資訊。
    費用調整時：結束舊記錄 (設 end_date) + 新增新記錄，自動保留歷史。
    """

    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', '月繳'
        BIMONTHLY = 'bimonthly', '雙月'
        SEMI_ANNUAL = 'semi_annual', '半年'
        ANNUAL = 'annual', '年繳'
        BIMONTHLY_AUTO = 'bimonthly_auto', '雙月(自動扣款)'
        SEMI_ANNUAL_PREPAID = 'semi_annual_prepaid', '半年(預繳收費)'

    client = models.ForeignKey(
        'bookkeeping.BookkeepingClient',
        on_delete=models.CASCADE,
        related_name='service_fees',
        verbose_name=_('記帳客戶'),
    )
    service_fee = models.IntegerField(_('服務費用'), default=0)
    ledger_fee = models.IntegerField(_('帳簿費用'), default=0)
    billing_months = models.IntegerField(
        _('收費月份'),
        default=13,
        help_text=_('若無特定月份可填寫 13')
    )
    billing_cycle = models.CharField(
        _('收費週期'),
        max_length=30,
        choices=BillingCycle.choices,
        default=BillingCycle.BIMONTHLY,
    )
    effective_date = models.DateField(_('生效日'), default=timezone.now)
    end_date = models.DateField(_('結束日'), blank=True, null=True)
    notes = models.TextField(_('備註'), blank=True)

    class Meta:
        verbose_name = _('服務費用')
        verbose_name_plural = _('服務費用')
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.client.name} - 服務費 {self.service_fee} / 帳簿費 {self.ledger_fee}"

    @property
    def is_active(self):
        today = timezone.now().date()
        if self.end_date and self.end_date < today:
            return False
        return self.effective_date <= today


class ClientBill(BaseModel):
    """客戶帳單主表"""

    class BillStatus(models.TextChoices):
        DRAFT = 'draft', '草稿'
        ISSUED = 'issued', '已開立'
        PAID = 'paid', '已收款'
        OVERDUE = 'overdue', '逾期'
        VOID = 'void', '已作廢'

    bill_no = models.CharField(
        _('帳單編號'), max_length=50, unique=True, blank=True
    )
    client = models.ForeignKey(
        'bookkeeping.BookkeepingClient',
        on_delete=models.CASCADE,
        related_name='bills',
        verbose_name=_('記帳客戶'),
    )
    year = models.IntegerField(_('年度'))
    month = models.IntegerField(_('月份'))
    bill_date = models.DateField(_('開立日期'), default=timezone.now)
    due_date = models.DateField(_('應繳日期'), blank=True, null=True)
    status = models.CharField(
        _('狀態'),
        max_length=20,
        choices=BillStatus.choices,
        default=BillStatus.DRAFT,
    )
    total_amount = models.DecimalField('合計金額', max_digits=12, decimal_places=0, default=0)
    quotation_data = models.JSONField('帳單明細', default=list, blank=True)
    cost_sharing_data = models.JSONField('公費分攤比例', default=list, blank=True)
    advance_payment_data = models.JSONField('代墊款明細', default=list, blank=True)
    is_ar_transferred = models.BooleanField('已拋轉 AR', default=False)
    is_posted = models.BooleanField('已過帳', default=False, help_text='標記是否已經拋轉應收帳款與傳票')
    notes = models.TextField('備註', blank=True, null=True)

    class Meta:
        verbose_name = '客戶帳單'
        verbose_name_plural = '客戶帳單'
        ordering = ['-year', '-month', '-client__name']
        unique_together = [['client', 'year', 'month']]

    def __str__(self):
        return f"{self.bill_no} - {self.client.name} ({self.year}/{self.month})"

    def save(self, *args, **kwargs):
        if not self.bill_no:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"BI{today_str}"
            last = ClientBill.objects.filter(
                bill_no__startswith=prefix
            ).order_by('-bill_no').first()
            if last:
                try:
                    seq = int(last.bill_no.replace(prefix, '')) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.bill_no = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    def recalculate_total(self):
        """重新計算帳單合計"""
        if self.quotation_data and isinstance(self.quotation_data, list) and len(self.quotation_data) > 0:
            self.total_amount = sum(
                int(item.get('amount', 0)) for item in self.quotation_data if isinstance(item, dict)
            )
        else:
            self.total_amount = sum(
                item.amount for item in self.items.all()
            )
        self.save(update_fields=['total_amount'])

    def to_ar_data(self):
        """拋轉至應收帳款的資料格式"""
        
        quotation_data = self.quotation_data
        if not quotation_data:
            quotation_data = [
                {
                    'service_name': f"2-{item.description}",
                    'amount': int(item.amount),
                    'remark': item.notes or '',
                }
                for item in self.items.all()
            ]

        return {
            'company_name': self.client.name,
            'unified_business_no': self.client.tax_id,
            'main_contact': self.client.contact_person,
            'mobile': self.client.mobile,
            'phone': self.client.phone,
            'address': self.client.correspondence_address,
            'line_id': self.client.line_id,
            'room_id': self.client.room_id,
            'quotation_data': quotation_data,
            'cost_sharing_data': self.cost_sharing_data or self.client.cost_sharing_data or [],
            'remarks': f"帳單編號：{self.bill_no}，客戶：{self.client.name}",
        }


class ClientBillItem(BaseModel):
    """帳單明細（子表）- 快照式紀錄"""

    bill = models.ForeignKey(
        ClientBill,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('帳單'),
    )
    service_fee_ref = models.ForeignKey(
        ServiceFee,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bill_items',
        verbose_name=_('來源服務費用'),
    )
    description = models.CharField(_('項目說明'), max_length=200)
    amount = models.DecimalField(
        _('金額'), max_digits=12, decimal_places=0, default=0
    )
    notes = models.CharField(_('備註'), max_length=255, blank=True)

    class Meta:
        verbose_name = _('帳單明細')
        verbose_name_plural = _('帳單明細')
        ordering = ['id']

    def __str__(self):
        return f"{self.description}: {self.amount}"
