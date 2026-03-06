from django.db import models
from django.utils import timezone
from core.models import BaseModel
from modules.basic_data.models import Customer

class DocumentDispatch(BaseModel):
    DISPATCH_METHOD_CHOICES = [
        ('郵局', '郵局'),
        ('掛號', '掛號'),
        ('快遞', '快遞'),
        ('親送', '親送'),
        ('其他', '其他'),
    ]

    date = models.DateField(default=timezone.now, verbose_name="發文日期")
    dispatch_method = models.CharField(max_length=20, choices=DISPATCH_METHOD_CHOICES, default='掛號', verbose_name="發信方式")
    
    class Meta:
        verbose_name = "發文紀錄"
        verbose_name_plural = "發文紀錄"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.get_dispatch_method_display()}"


class DocumentDispatchItem(BaseModel):
    dispatch = models.ForeignKey(DocumentDispatch, on_delete=models.CASCADE, related_name='items', verbose_name="發文紀錄")
    is_absorbed_by_customer = models.BooleanField(default=False, verbose_name="是否客戶吸收")
    postage = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="郵資費用")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='dispatches', verbose_name="客戶名稱")
    tax_id = models.CharField(max_length=20, blank=True, verbose_name="統一編號")
    address = models.CharField(max_length=255, blank=True, verbose_name="寄送地址")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="聯絡人")
    recipient = models.CharField(max_length=100, blank=True, verbose_name="收件人")
    custom_message = models.CharField(max_length=255, blank=True, verbose_name="自訂訊息")
    is_notified = models.BooleanField(default=False, verbose_name="通知客戶")

    class Meta:
        verbose_name = "發文項目"
        verbose_name_plural = "發文項目"

    def __str__(self):
        return f"{self.customer.name} - {self.address}"


class DocumentDispatchImage(models.Model):
    document = models.ForeignKey(DocumentDispatch, on_delete=models.CASCADE, related_name='images', verbose_name='發文紀錄')
    image = models.ImageField(upload_to='dispatch_images/%Y/%m/', verbose_name='圖片檔案')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上傳時間')
    
    class Meta:
        verbose_name = '發文紀錄圖片'
        verbose_name_plural = '發文紀錄圖片'
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.document.date} - Image {self.id}"
