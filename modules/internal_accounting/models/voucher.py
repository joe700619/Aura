from django.db import models
from core.models import BaseModel

class Voucher(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', '草稿'
        POSTED = 'POSTED', '已過帳'
        
    class Source(models.TextChoices):
        MANUAL = 'MANUAL', '人工輸入'
        SYSTEM = 'SYSTEM', '系統拋轉'
        YEAR_END_CLOSING = 'YEAR_END_CLOSING', '年度結轉'
        DEPRECIATION = 'DEPRECIATION', '提列折舊'
        COLLECTION = 'COLLECTION', '收款過帳'

    voucher_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name="傳票編號")
    date = models.DateField(verbose_name="日期")
    description = models.TextField(blank=True, verbose_name="摘要")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="狀態")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL, verbose_name="來源")
    
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, verbose_name="建立者")

    class Meta:
        verbose_name = "會計傳票"
        verbose_name_plural = "會計傳票"
        ordering = ['-date', '-voucher_no']

    def clean(self):
        super().clean()
        if self.date:
            from .period import AccountingPeriod
            from django.core.exceptions import ValidationError
            period = AccountingPeriod.objects.filter(year=self.date.year, month=self.date.month).first()
            if period and period.status == AccountingPeriod.Status.CLOSED:
                raise ValidationError({"date": f"{self.date.year}年度{self.date.month}月份已關帳，無法新增或修改該期間傳票。"})

    def __str__(self):
        return self.voucher_no

class VoucherImage(models.Model):
    voucher = models.ForeignKey(Voucher, related_name='images', on_delete=models.CASCADE, verbose_name="所屬傳票")
    image = models.ImageField(upload_to='vouchers/%Y/%m/', verbose_name="圖片檔案")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上傳時間")

    class Meta:
        verbose_name = "傳票夾檔圖片"
        verbose_name_plural = "傳票夾檔圖片"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.voucher.voucher_no} - Image {self.id}"
