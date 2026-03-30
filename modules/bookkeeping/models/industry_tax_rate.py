from django.db import models
from django.utils.translation import gettext_lazy as _

class IndustryTaxRate(models.Model):
    """
    各業別稅率標準 (Master Data)
    """
    industry_code = models.CharField(_('行業代號'), max_length=20)
    industry_name = models.CharField(_('行業名稱'), max_length=100)
    applicable_year = models.IntegerField(_('適用起始年度'), help_text=_('例如: 112, 113'))
    
    book_review_profit_rate = models.DecimalField(
        _('擴大書審純益率(%)'), 
        max_digits=5, 
        decimal_places=2,
        null=True, blank=True
    )
    net_profit_rate = models.DecimalField(
        _('淨利率(%)'), 
        max_digits=5, 
        decimal_places=2,
        null=True, blank=True
    )
    income_standard = models.DecimalField(
        _('所得額標準(%)'), 
        max_digits=5, 
        decimal_places=2,
        null=True, blank=True
    )

    class Meta:
        verbose_name = _('各業別稅率標準')
        verbose_name_plural = _('各業別稅率標準')
        constraints = [
            models.UniqueConstraint(
                fields=['industry_code', 'applicable_year'],
                name='unique_bookkeeping_industry_rate_per_year'
            )
        ]
        ordering = ['-applicable_year', 'industry_code']

    def __str__(self):
        return f"{self.applicable_year} - {self.industry_code} {self.industry_name}"
