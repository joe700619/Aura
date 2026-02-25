from django.db import models
from django.utils.translation import gettext_lazy as _

class VATEntityChange(models.Model):
    # 1. Basic Data
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True)
    company_name = models.CharField(_('公司名稱'), max_length=255, blank=True)
    tax_id = models.CharField(_('稅籍編號'), max_length=50, blank=True)
    registered_address = models.CharField(_('登記地址'), max_length=255, blank=True)

    # 2. Contact Data
    assistant_name = models.CharField(_('助理人員'), max_length=100, blank=True)
    email = models.EmailField(_('Email'), blank=True)

    # 3. Other
    CASE_TYPE_CHOICES = [
        ('setup', _('設立')),
        ('rep_change', _('負責人變更')),
        ('name_change', _('名稱變更')),
        ('addr_change', _('所在地變更')),
        ('item_change', _('營業項目變更')),
        ('org_change', _('組織變更')),
        ('cap_increase', _('增資變更')),
        ('cap_decrease', _('減資變更')),
        ('tax_unit_to_vat', _('扣繳單位變更為營業人')),
        ('online_sales_change', _('網路銷售資訊變更')),
        ('other', _('其他')),
    ]
    case_types = models.JSONField(_('案件種類'), default=list, blank=True)
    registration_no = models.CharField(_('登記單號'), max_length=20, blank=True)
    is_completed = models.BooleanField(_('完成狀態'), default=False)

    # 4. Note
    note = models.TextField(_('備註'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('營業人變更登記')
        verbose_name_plural = _('營業人變更登記')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.registration_no} - {self.company_name}"
