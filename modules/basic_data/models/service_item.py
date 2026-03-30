from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

class ServiceItem(models.Model):
    class Department(models.IntegerChoices):
        VISA = 1, _('簽證')
        BOOKKEEPING = 2, _('記帳')
        REGISTRATION = 3, _('登記')
        ADVANCE_PAYMENT = 4, _('代墊')
        PRE_COLLECTION = 5, _('預收')

    service_id = models.CharField(_('服務項目編號'), max_length=20, unique=True, editable=False)
    department = models.IntegerField(_('部門分類'), choices=Department.choices)
    name = models.CharField(_('服務項目名稱'), max_length=255, unique=True)
    reference_fee = models.DecimalField(_('參考公費'), max_digits=10, decimal_places=0, default=0)
    remark = models.TextField(_('備註'), blank=True, null=True)
    
    # Checkbox fields
    is_company_law_22_1 = models.BooleanField(_('是否需申報公司法22-1'), default=False)
    is_money_laundering_check = models.BooleanField(_('是否執行洗錢防制法檢查'), default=False)
    is_business_entity_change = models.BooleanField(_('是否需營業人變更'), default=False)
    is_shareholder_list_change = models.BooleanField(_('是否變更股東名簿'), default=False)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _('服務項目')
        verbose_name_plural = _('服務項目')
        ordering = ['service_id']

    def __str__(self):
        return f"{self.service_id} {self.name}"

    def save(self, *args, **kwargs):
        if not self.service_id:
            last_item = ServiceItem.objects.all().order_by('-service_id').first()
            if last_item and last_item.service_id.startswith('P'):
                try:
                    last_num = int(last_item.service_id[1:])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = 1
            self.service_id = f'P{new_num:05d}'
        super().save(*args, **kwargs)
