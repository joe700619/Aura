from django.db import models
from core.models import BaseModel

class AccountingPeriod(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', '開帳'
        CLOSED = 'CLOSED', '已關帳'

    year = models.IntegerField(verbose_name="年度")
    month = models.IntegerField(verbose_name="月份")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, verbose_name="狀態")
    depreciation_done = models.BooleanField(default=False, verbose_name="已提列折舊")

    class Meta:
        verbose_name = "會計期間"
        verbose_name_plural = "會計期間"
        unique_together = [['year', 'month']]
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.year}/{self.month:02d} ({self.get_status_display()})"
