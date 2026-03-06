from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class AttendanceRecord(BaseModel):
    """
    出勤紀錄
    記錄員工打卡（上班/下班）、來源（Line/Web/補卡）。
    """

    SOURCE_CHOICES = [
        ('web', '網頁打卡'),
        ('line', 'Line 打卡'),
        ('makeup', '補卡'),
    ]

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name=_('員工'),
    )
    date = models.DateField(_('出勤日期'))
    clock_in = models.TimeField(_('上班打卡'), null=True, blank=True)
    clock_out = models.TimeField(_('下班打卡'), null=True, blank=True)
    source = models.CharField(
        _('打卡來源'),
        max_length=10,
        choices=SOURCE_CHOICES,
        default='web',
    )

    # 補卡相關
    makeup_reason = models.TextField(
        _('補卡事由'),
        blank=True,
        default='',
        help_text=_('補卡時必須填寫事由'),
    )
    is_approved = models.BooleanField(_('是否已核准'), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_attendances',
        verbose_name=_('核准人'),
    )

    note = models.TextField(_('備註'), blank=True, default='')

    class Meta:
        ordering = ['-date', 'employee__employee_number']
        verbose_name = _('出勤紀錄')
        verbose_name_plural = _('出勤紀錄')
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date'],
                name='unique_employee_date_attendance',
            )
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.date}"

    @property
    def status_display(self):
        """顯示出勤狀態"""
        if self.clock_in and self.clock_out:
            return '正常'
        elif self.clock_in:
            return '未打下班卡'
        elif self.clock_out:
            return '未打上班卡'
        return '未出勤'
