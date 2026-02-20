from django.db import models
from django.utils.translation import gettext_lazy as _

class PaymentTransaction(models.Model):
    class PaymentType(models.TextChoices):
        ECPAY = 'ECPay', _('綠界科技')
        NEWEBPAY = 'NewebPay', _('藍新金流')

    merchant_trade_no = models.CharField(_('交易編號'), max_length=50, primary_key=True)
    trade_date = models.DateTimeField(_('交易時間'), auto_now_add=True)
    total_amount = models.IntegerField(_('交易金額'))
    trade_desc = models.CharField(_('交易描述'), max_length=200)
    item_name = models.CharField(_('商品名稱'), max_length=200)
    
    rtn_code = models.IntegerField(_('交易狀態碼'), default=0, help_text="1: 成功, 其他: 失敗/待付款")
    rtn_msg = models.CharField(_('交易訊息'), max_length=200, blank=True)
    
    payment_type = models.CharField(_('支付方式'), max_length=20, choices=PaymentType.choices, default=PaymentType.ECPAY)
    
    has_shipping = models.BooleanField(_('含運費'), default=False)
    
    # Polymorphic-like relation to link back to the source (e.g., Progress, Order)
    related_app = models.CharField(_('關聯App'), max_length=50, blank=True)
    related_model = models.CharField(_('關聯模型'), max_length=50, blank=True)
    related_id = models.CharField(_('關聯ID'), max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('交易紀錄')
        verbose_name_plural = _('交易紀錄')
        ordering = ['-trade_date']

    def __str__(self):
        return f"{self.merchant_trade_no} - ${self.total_amount}"
