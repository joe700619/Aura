from django.db import models

class Account(models.Model):
    class Category(models.TextChoices):
        ASSET = 'ASSET', '資產'
        LIABILITY = 'LIABILITY', '負債'
        EQUITY = 'EQUITY', '權益'
        REVENUE = 'REVENUE', '營收'
        COST = 'COST', '成本'
        EXPENSE = 'EXPENSE', '費用'
        NON_OP_INC = 'NON_OP_INC', '營業外收入'
        NON_OP_EXP = 'NON_OP_EXP', '營業外支出'
        TAX = 'TAX', '所得稅費用'

    class AuxiliaryType(models.TextChoices):
        NONE = 'NONE', '無'
        PARTNER = 'PARTNER', '對象 (客戶/廠商/統編)'
        DEPARTMENT = 'DEPT', '部門'
        PROJECT = 'PROJECT', '專案'
        FIXED_ASSET = 'ASSET', '固定資產'

    code = models.CharField(max_length=20, primary_key=True, verbose_name="科目代號")
    name = models.CharField(max_length=100, verbose_name="科目名稱")
    category = models.CharField(max_length=20, choices=Category.choices, verbose_name="類別")
    auxiliary_type = models.CharField(
        max_length=20, 
        choices=AuxiliaryType.choices, 
        default=AuxiliaryType.NONE,
        verbose_name="輔助核算類別"
    )
    is_active = models.BooleanField(default=True, verbose_name="啟用中")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "會計科目"
        verbose_name_plural = "會計科目"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} {self.name}"
