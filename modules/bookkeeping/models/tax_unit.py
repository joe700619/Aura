from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class TaxUnit(BaseModel):
    """國稅局轄區對照表

    full_code = city_id + unit_code，例如 A0300（台北市信義分局）
    查詢時直接用 full_code，不再透過稅籍編號推算。
    """

    city_id = models.CharField(_('城市代號'), max_length=1)
    unit_code = models.CharField(_('稅籍單位代碼'), max_length=4)
    dept_id = models.CharField(_('稽徵所代號'), max_length=5)
    unit_name = models.CharField(_('單位名稱'), max_length=50)
    bureau_name = models.CharField(_('國稅局名稱'), max_length=50, blank=True, default='',
                                   help_text=_('例如：財政部臺北國稅局'))

    class Meta:
        verbose_name = _('國稅局對照表')
        verbose_name_plural = _('國稅局對照表')
        ordering = ['city_id', 'unit_code']
        unique_together = [('city_id', 'unit_code')]

    @property
    def full_code(self):
        return f"{self.city_id}{self.unit_code}"

    def __str__(self):
        return f"{self.full_code} {self.unit_name}"
