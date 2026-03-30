from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class SealProcurement(BaseModel):
    """印章採購單 - 主表"""

    YES_NO_CHOICES = [
        (True, '是'),
        (False, '否'),
    ]

    # Card 1: 基本資料
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, default='')
    company_name = models.CharField(_('公司名稱'), max_length=100, blank=True, default='')
    line_id = models.CharField(_('Line ID'), max_length=50, blank=True, default='')
    room_id = models.CharField(_('Room ID'), max_length=50, blank=True, default='')

    # Card 2: 聯絡人
    main_contact = models.CharField(_('主要聯絡人'), max_length=50, blank=True, default='')
    mobile = models.CharField(_('手機'), max_length=20, blank=True, default='')
    phone = models.CharField(_('電話'), max_length=30, blank=True, default='')
    address = models.CharField(_('通訊地址'), max_length=200, blank=True, default='')

    # Card 3: 其他
    transfer_to_advance = models.BooleanField(_('轉為代墊款'), default=False)
    is_advance_transferred = models.BooleanField(_('已拋轉代墊款'), default=False)
    transfer_to_inventory = models.BooleanField(_('轉為庫存'), default=False)
    seal_cost_subtotal = models.DecimalField(_('印章費用小計'), max_digits=10, decimal_places=0, default=0)
    is_paid = models.BooleanField(_('是否已付款'), default=False)

    # 備註
    note = models.TextField(_('備註'), blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('印章採購單')
        verbose_name_plural = _('印章採購單')

    def __str__(self):
        return f"{self.company_name} - {self.created_at.strftime('%Y-%m-%d') if self.created_at else ''}"

    def recalculate_subtotal(self):
        """Recalculate seal_cost_subtotal from purchase items only."""
        total = sum(item.subtotal for item in self.items.filter(movement_type='purchase'))
        self.seal_cost_subtotal = total
        self.save(update_fields=['seal_cost_subtotal'])


class SealProcurementItem(BaseModel):
    """印章請購明細 - 子表"""

    MOVEMENT_TYPE_CHOICES = [
        ('purchase', '採購'),
        ('customer_provided', '客戶提供'),
        ('return_to_customer', '歸還客戶'),
        ('lend_out', '借出'),
        ('borrow_in', '借入'),
        ('surplus', '盤盈'),
        ('deficit', '盤虧'),
    ]

    SEAL_TYPE_CHOICES = [
        ('large_self', '大章(自留)'),
        ('small_self', '小章(自留)'),
        ('large_reg', '大章(登記)'),
        ('small_reg', '小章(登記)'),
        ('invoice', '發票章'),
    ]

    SEAL_DEFAULT_PRICES = {
        'large_self': 150,
        'small_self': 50,
        'large_reg': 150,
        'small_reg': 50,
        'invoice': 180,
    }

    procurement = models.ForeignKey(
        SealProcurement,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('採購單')
    )
    is_absorbed_by_customer = models.BooleanField(_('客戶吸收'), default=False)
    movement_type = models.CharField(_('異動類別'), max_length=30, choices=MOVEMENT_TYPE_CHOICES, default='purchase')
    seal_type = models.CharField(_('印章種類'), max_length=20, choices=SEAL_TYPE_CHOICES, default='large_self')
    quantity = models.IntegerField(_('數量'), default=1)
    name_or_address = models.CharField(_('名稱/地址'), max_length=200, blank=True, default='')
    unit_price = models.DecimalField(_('單價'), max_digits=10, decimal_places=0, default=150)
    subtotal = models.DecimalField(_('合計'), max_digits=10, decimal_places=0, default=0)

    class Meta:
        verbose_name = _('印章請購明細')
        verbose_name_plural = _('印章請購明細')

    def save(self, *args, **kwargs):
        if self.movement_type == 'purchase':
            self.subtotal = self.quantity * self.unit_price
        else:
            self.subtotal = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.get_seal_type_display()} x {self.quantity}"
