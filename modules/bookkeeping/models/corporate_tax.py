from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel
from .progress import BookkeepingYear

class CorporateTaxFiling(BaseModel):
    """營所稅申報主表 (Corporate Tax Filing)"""
    year_record = models.OneToOneField(
        BookkeepingYear,
        on_delete=models.CASCADE,
        related_name='corporate_tax_filing',
        verbose_name=_('所屬年度')
    )
    
    industry_code = models.CharField(_('行業代號'), max_length=20, blank=True, default='')
    industry_name = models.CharField(_('行業名稱'), max_length=100, blank=True, default='')

    industry_profit_rate = models.DecimalField(_('擴大書審純益率 (%)'), max_digits=5, decimal_places=2, default=6.00)
    income_standard_rate = models.DecimalField(_('所得額標準 (%)'), max_digits=5, decimal_places=2, default=8.00)
    net_profit_rate = models.DecimalField(_('同業利潤標準淨利率 (%)'), max_digits=5, decimal_places=2, default=10.00)
    
    tax_rate = models.DecimalField(_('營所稅率 (%)'), max_digits=5, decimal_places=2, default=20.00)

    class Meta:
        verbose_name = _('營所稅申報設定')
        verbose_name_plural = _('營所稅申報設定')

    def __str__(self):
        return f"{self.year_record} - 營所稅設定"


class TaxAdjustmentEntry(BaseModel):
    """申報明細/科目調整表"""
    filing = models.ForeignKey(
        CorporateTaxFiling,
        on_delete=models.CASCADE,
        related_name='adjustments',
        verbose_name=_('營所稅申報')
    )
    
    # 這裡先使用簡單的 CharField 儲存科目代碼與名稱。
    account_code = models.CharField(_('科目代碼'), max_length=20)
    account_name = models.CharField(_('科目名稱'), max_length=100)
    
    book_amount = models.DecimalField(_('帳列金額'), max_digits=15, decimal_places=0, default=0)
    excluded_amount = models.DecimalField(_('帳外剔除金額'), max_digits=15, decimal_places=0, default=0)
    
    class Meta:
        verbose_name = _('申報調整明細')
        verbose_name_plural = _('申報調整明細')
        unique_together = ('filing', 'account_code')
        ordering = ['account_code']

    def __str__(self):
        return f"{self.account_code} {self.account_name}"

    @property
    def declared_amount(self):
        """申報數 = 帳列金額 - 帳外剔除"""
        return self.book_amount - self.excluded_amount
