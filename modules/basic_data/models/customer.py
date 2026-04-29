from django.db import models
from core.models import BaseModel

class Customer(BaseModel):
    """Customer / Client Basic Data"""
    
    class SourceChoices(models.TextChoices):
        ESTABLISHED_BY_US = 'ESTABLISHED', '本所設立'
        TRANSFERRED_IN = 'TRANSFERRED', '他所轉入'

    # 一、基本資訊
    tax_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="統一編號")
    name = models.CharField(max_length=100, verbose_name="公司名稱")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="電話號碼")
    mobile = models.CharField(max_length=50, blank=True, null=True, verbose_name="手機號碼")
    source = models.CharField(
        max_length=20, 
        choices=SourceChoices.choices, 
        default=SourceChoices.ESTABLISHED_BY_US,
        verbose_name="客戶來源"
    )
    line_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="LineID")
    room_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="RoomID")
    
    # 登記地址
    registered_zip = models.CharField(max_length=10, blank=True, null=True, verbose_name="登記地址-郵遞區號")
    registered_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="登記地址")
    
    # 通訊地址
    correspondence_zip = models.CharField(max_length=10, blank=True, null=True, verbose_name="通訊地址-郵遞區號")
    correspondence_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="通訊地址")

    # 二、帳單資訊
    bank_account_last5 = models.CharField(max_length=20, blank=True, null=True, verbose_name="帳號後五碼")
    labor_ins_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="勞保代號")
    health_ins_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="健保代號")

    # 三、聯絡人資訊 (預留)
    contact_person = models.CharField(max_length=50, blank=True, null=True, verbose_name="聯絡人 (預留)")
    notes = models.TextField(blank=True, null=True, verbose_name="備註")

    class Meta:
        verbose_name = "客戶資料"
        verbose_name_plural = "客戶資料"
        ordering = ['-created_at']

    def __str__(self):
        return self.name
