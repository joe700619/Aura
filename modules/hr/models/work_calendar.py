from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class WorkCalendar(BaseModel):
    """
    工作日曆
    管理國定假日、補班日等特殊日期。
    一般工作日（週一到週五）不需建立，
    只需建立「非正常」的日期：國定假日、補班日。
    """

    DAY_TYPE_CHOICES = [
        ('national_holiday', '國定假日'),
        ('makeup_workday', '補班日'),
    ]

    date = models.DateField(_('日期'), unique=True)
    day_type = models.CharField(
        _('日期類型'),
        max_length=20,
        choices=DAY_TYPE_CHOICES,
    )
    description = models.CharField(_('說明'), max_length=100, blank=True, default='')
    year = models.IntegerField(_('年度'), editable=False)

    class Meta:
        ordering = ['-date']
        verbose_name = _('工作日曆')
        verbose_name_plural = _('工作日曆')

    def save(self, *args, **kwargs):
        self.year = self.date.year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} - {self.get_day_type_display()} ({self.description})"

    @staticmethod
    def is_workday(date):
        """
        判斷某日是否為工作日：
        - 若該日有 WorkCalendar 紀錄 → 看 day_type
        - 若無紀錄 → 週一~五為工作日，六日為休息日
        """
        try:
            record = WorkCalendar.objects.get(date=date)
            return record.day_type == 'makeup_workday'
        except WorkCalendar.DoesNotExist:
            # 0=Monday, 5=Saturday, 6=Sunday
            return date.weekday() < 5

    @staticmethod
    def get_workdays_in_month(year, month):
        """計算指定年月的工作日數"""
        import calendar
        _, days_in_month = calendar.monthrange(year, month)
        from datetime import date as dt_date
        count = 0
        for day in range(1, days_in_month + 1):
            d = dt_date(year, month, day)
            if WorkCalendar.is_workday(d):
                count += 1
        return count
