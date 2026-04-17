from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class ShareholderRegister(BaseModel):
    class ServiceStatus(models.TextChoices):
        INCLUDED = 'INCLUDED', _('本所客戶')
        EXCLUDED = 'EXCLUDED', _('已非本所服務')

    class CompletionStatus(models.TextChoices):
        COMPLETED = 'COMPLETED', _('已完成')
        UNCOMPLETED = 'UNCOMPLETED', _('未完成')

    company_name = models.CharField(_('公司名稱'), max_length=100)
    unified_business_no = models.CharField(_('統一編號'), max_length=20, unique=True)
    line_id = models.CharField(_('Line ID'), max_length=50, blank=True, null=True)
    room_id = models.CharField(_('Room ID'), max_length=50, blank=True, null=True)
    service_status = models.CharField(
        _('承接狀態'),
        max_length=20,
        choices=ServiceStatus.choices,
        default=ServiceStatus.INCLUDED
    )
    completion_status = models.CharField(
        _('完成狀態'),
        max_length=20,
        choices=CompletionStatus.choices,
        default=CompletionStatus.UNCOMPLETED
    )

    class Meta:
        verbose_name = _('股東名簿查詢')
        verbose_name_plural = _('股東名簿查詢')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.unified_business_no})"


class DirectorSupervisor(models.Model):
    class Title(models.TextChoices):
        CHAIRMAN   = 'CHAIRMAN',   _('董事長')
        DIRECTOR   = 'DIRECTOR',   _('董事')
        SUPERVISOR = 'SUPERVISOR', _('監察人')
        MANAGER    = 'MANAGER',    _('經理人')

    register = models.ForeignKey(
        ShareholderRegister,
        on_delete=models.CASCADE,
        related_name='directors',
        verbose_name=_('股東名簿'),
    )
    title = models.CharField(_('職稱'), max_length=20, choices=Title.choices)
    name = models.CharField(_('姓名'), max_length=50)
    id_number = models.CharField(_('身分證字號'), max_length=20, blank=True)
    nationality = models.CharField(_('國籍'), max_length=50, blank=True)
    birth_date = models.DateField(_('出生年月日'), null=True, blank=True)
    shares_held = models.PositiveIntegerField(_('持有股份'), default=0)
    entity_name = models.CharField(_('所代表法人'), max_length=100, blank=True)
    entity_no = models.CharField(_('代表法人統編'), max_length=20, blank=True)
    order = models.PositiveIntegerField(_('排序'), default=0)

    class Meta:
        verbose_name = _('董監事')
        verbose_name_plural = _('董監事名單')
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.get_title_display()} {self.name}"
