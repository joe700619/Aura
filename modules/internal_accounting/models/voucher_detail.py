from django.db import models

class VoucherDetail(models.Model):
    voucher = models.ForeignKey('internal_accounting.Voucher', related_name='details', on_delete=models.CASCADE, verbose_name="傳票")
    account = models.ForeignKey('internal_accounting.Account', on_delete=models.PROTECT, verbose_name="科目")
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="借方")
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="貸方")
    
    company_id = models.CharField(max_length=50, blank=True, verbose_name="對象/統編")
    department = models.CharField(max_length=50, blank=True, verbose_name="部門")
    project = models.CharField(max_length=50, blank=True, verbose_name="專案")
    
    remark = models.CharField(max_length=255, blank=True, verbose_name="備註")

    class Meta:
        verbose_name = "傳票分錄"
        verbose_name_plural = "傳票分錄"

    def __str__(self):
        return f"{self.account.name} - D:{self.debit} C:{self.credit}"
