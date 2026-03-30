import os
from django.db import models
from django.utils import timezone
from modules.basic_data.models.customer import Customer
from core.models import BaseModel


class DocumentReceipt(BaseModel):
    CATEGORY_CHOICES = [
        ('營業稅憑證', '營業稅憑證'),
        ('會計帳冊', '會計帳冊'),
        ('補寄憑證', '補寄憑證'),
        ('國稅局公文', '國稅局公文'),
        ('經濟部公文', '經濟部公文'),
        ('法院公文', '法院公文'),
        ('其他公文', '其他公文'),
        ('事務所信件', '事務所信件'),
        ('事務所帳單', '事務所帳單'),
        ('各類函證', '各類函證'),
        ('其他', '其他'),
    ]
    STATUS_CHOICES = [
        ('待處理', '待處理'),
        ('處理中', '處理中'),
        ('已結案', '已結案'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="客戶")
    receipt_date = models.DateField(default=timezone.now, verbose_name="收文日期")
    subject = models.CharField(max_length=255, verbose_name="信件主旨")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True, verbose_name="信件分類")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='待處理', verbose_name="處理狀態")
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")
    attachment = models.FileField(upload_to='document_receipts/%Y/%m/', blank=True, null=True, verbose_name="附件")
    is_line_notified = models.BooleanField(default=False, verbose_name="Line 通知狀態")

    class Meta:
        verbose_name = "收文紀錄"
        verbose_name_plural = "收文紀錄"
        ordering = ['-receipt_date', '-created_at']

    def __str__(self):
        return f"{self.customer} - {self.subject} ({self.receipt_date})"


class DocumentReceiptAttachment(models.Model):
    receipt = models.ForeignKey(DocumentReceipt, on_delete=models.CASCADE, related_name='attachments', verbose_name="收文紀錄")
    file = models.FileField(upload_to='document_receipts/%Y/%m/', verbose_name="附件")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上傳時間")

    class Meta:
        verbose_name = "收文附件"
        verbose_name_plural = "收文附件"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.receipt} - {os.path.basename(self.file.name)}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def is_image(self):
        return self.file.name.lower().rsplit('.', 1)[-1] in ('jpg', 'jpeg', 'png', 'gif', 'webp')
