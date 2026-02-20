from django.db import models
from simple_history.models import HistoricalRecords
from .customer import Customer

class Contact(models.Model):
    """Contact Person Data"""
    
    name = models.CharField(max_length=100, verbose_name="姓名")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="電話")
    mobile = models.CharField(max_length=20, blank=True, null=True, verbose_name="手機")
    fax = models.CharField(max_length=20, blank=True, null=True, verbose_name="傳真")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="通訊地址")
    
    # Linked Company
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='contacts', 
        verbose_name="公司名稱"
    )
    
    tax_id = models.CharField(max_length=20, verbose_name="統一編號", blank=True, null=True)
    notes = models.TextField(verbose_name="備註", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False, verbose_name="是否刪除")
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = "聯絡人"
        verbose_name_plural = "聯絡人"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.customer.name})"
