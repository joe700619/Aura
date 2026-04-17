from django.db import models
from core.models import BaseModel

class FixedAsset(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', '使用中'
        SCRAPPED = 'SCRAPPED', '已報廢'
        SOLD = 'SOLD', '已出售'

    asset_no = models.CharField(max_length=50, unique=True, verbose_name="財產編號")
    name = models.CharField(max_length=100, verbose_name="財產名稱")
    purchase_date = models.DateField(verbose_name="取得日期")
    
    cost = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="取得成本")
    salvage_value = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="預估殘值")
    useful_life_months = models.IntegerField(verbose_name="耐用月數")
    
    accumulated_depreciation = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="累計折舊")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="狀態")

    # 科目設定：預設每個資產可以獨立設定，但也可以有預設值，前端再帶入
    depreciation_expense_account_code = models.CharField(max_length=20, blank=True, verbose_name="折舊費用科目")
    accumulated_depreciation_account_code = models.CharField(max_length=20, blank=True, verbose_name="累計折舊科目")

    class Meta:
        verbose_name = "財產目錄"
        verbose_name_plural = "財產目錄"
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.asset_no} - {self.name}"

    @property
    def net_value(self):
        return self.cost - self.accumulated_depreciation

    @property
    def depreciable_amount(self):
        return self.cost - self.salvage_value

    @property
    def is_fully_depreciated(self):
        return self.net_value <= self.salvage_value

    @property
    def monthly_depreciation(self):
        if self.useful_life_months > 0 and self.depreciable_amount > 0:
            return round(self.depreciable_amount / self.useful_life_months)
        return 0

    @property
    def depreciation_progress_pct(self):
        if self.depreciable_amount > 0:
            pct = int(self.accumulated_depreciation / self.depreciable_amount * 100)
            return min(pct, 100)
        return 0
