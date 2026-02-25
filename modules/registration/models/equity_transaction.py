from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import date

class EquityTransaction(models.Model):
    class OrganizationType(models.TextChoices):
        LTD = 'LTD', _('有限公司')
        CORP = 'CORP', _('股份有限公司')

    class TransactionReason(models.TextChoices):
        SETUP = 'SETUP', _('設立')
        CAPITAL_INCREASE = 'CAPITAL_INCREASE', _('增資')
        CAPITAL_REDUCTION = 'CAPITAL_REDUCTION', _('減資')
        BUY = 'BUY', _('買入')
        SELL = 'SELL', _('賣出')
        GIFT = 'GIFT', _('贈與')
        BEQUEST = 'BEQUEST', _('受贈')
        MERGER_INCREASE = 'MERGER_INCREASE', _('合併增加')
        MERGER_DECREASE = 'MERGER_DECREASE', _('合併減少')
        SPLIT_INCREASE = 'SPLIT_INCREASE', _('分割增加')
        SPLIT_DECREASE = 'SPLIT_DECREASE', _('分割減少')
        OTHER_INCREASE = 'OTHER_INCREASE', _('其他增加')
        OTHER_DECREASE = 'OTHER_DECREASE', _('其他減少')

    class StockType(models.TextChoices):
        COMMON = 'COMMON', _('普通股')
        PREFERRED = 'PREFERRED', _('特別股')

    shareholder_register = models.ForeignKey('registration.ShareholderRegister', on_delete=models.CASCADE, related_name='equity_transactions', verbose_name=_('股東名簿查詢'), null=True, blank=True)

    # Card 2: Shareholder Info

    # Card 2: Shareholder Info
    shareholder_name = models.CharField(_('姓名'), max_length=100)
    shareholder_id_number = models.CharField(_('身份證字號'), max_length=20)
    shareholder_address = models.CharField(_('地址'), max_length=255, blank=True, null=True)

    # Card 3: Transaction Info
    transaction_date = models.DateField(_('交易日期'), default=date.today)
    organization_type = models.CharField(_('組織種類'), max_length=10, choices=OrganizationType.choices)
    transaction_reason = models.CharField(_('交易事由'), max_length=20, choices=TransactionReason.choices)
    stock_type = models.CharField(_('股票種類'), max_length=10, choices=StockType.choices)
    share_count = models.IntegerField(_('股數'))
    unit_price = models.DecimalField(_('單價'), max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(_('合計'), max_digits=12, decimal_places=2)

    # Tracking & Status
    registration_no = models.CharField(_('登記案件編號'), max_length=50, blank=True, null=True)
    is_completed = models.BooleanField(_('是否完成'), default=False)

    note = models.TextField(_('備註'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('股權交易')
        verbose_name_plural = _('股權交易')
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        company = self.shareholder_register.company_name if self.shareholder_register else "Unknown Company"
        return f"{company} - {self.shareholder_name} - {self.get_transaction_reason_display()}"
