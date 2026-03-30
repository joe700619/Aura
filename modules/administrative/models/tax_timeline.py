from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class TaxTemplate(BaseModel):
    """
    任務範本：例如「營業稅申報」、「營所稅申報」
    """
    class SourceChoices(models.TextChoices):
        MANUAL = 'manual', _('手動更新')
        BUSINESS_TAX = 'business_tax', _('營業稅模組')
        BOOKKEEPING = 'bookkeeping', _('記帳模組')
        
    name = models.CharField(_("任務名稱"), max_length=100)
    is_recurring = models.BooleanField(_("是否為週期性"), default=True)
    recurring_months = models.CharField(_("執行月份"), max_length=50, help_text=_("例如: 1,3,5,7,9,11"))
    deadline_day = models.IntegerField(_("截止日期(日)"), default=15)
    description = models.TextField(_("備註說明"), blank=True)
    source_type = models.CharField(_("資料來源類型"), max_length=20, choices=SourceChoices.choices, default=SourceChoices.MANUAL)

    class Meta:
        verbose_name = _('任務範本')
        verbose_name_plural = _('任務範本')

    def __str__(self):
        return self.name

class TaxTaskInstance(BaseModel):
    """
    實際產出的任務：例如「113年3-4月營業稅」
    """
    template = models.ForeignKey(TaxTemplate, on_delete=models.CASCADE, verbose_name=_("任務範本"), related_name='instances')
    title = models.CharField(_("任務標題"), max_length=200)
    year = models.IntegerField(_("年度"))
    month = models.IntegerField(_("月份"))
    deadline = models.DateField(_("正式截止日"))
    
    is_completed = models.BooleanField(_("是否全數完工"), default=False)
    
    # 進度快照
    total_clients = models.IntegerField(_("總客戶數"), default=0)
    completed_clients = models.IntegerField(_("已完成數"), default=0)
    
    remarks = models.TextField(_("備註"), blank=True)

    class Meta:
        ordering = ['deadline']
        verbose_name = _('任務實例')
        verbose_name_plural = _('任務實例')
        unique_together = [['template', 'year', 'month']]

    def __str__(self):
        return self.title
