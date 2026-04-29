from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class ClientTaxEvent(BaseModel):
    title = models.CharField(_("事件標題"), max_length=200)
    deadline = models.DateField(_("截止日期"))
    urgent_days = models.IntegerField(
        _("緊急天數"), default=14,
        help_text=_("距截止日幾天內顯示緊急標記")
    )
    is_active = models.BooleanField(_("啟用"), default=True)
    sort_order = models.IntegerField(_("排序"), default=0)

    class Meta:
        ordering = ['deadline', 'sort_order']
        verbose_name = _('客戶行事曆事件')
        verbose_name_plural = _('客戶行事曆事件')

    def __str__(self):
        return f"{self.title}（{self.deadline}）"

    def is_urgent_on(self, today):
        return 0 <= (self.deadline - today).days <= self.urgent_days
