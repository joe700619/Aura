from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
import uuid

class Progress(models.Model):
    class ProgressStatus(models.IntegerChoices):
        NEW_CASE = 0, _('新接案')
        DISCUSSING = 1, _('討論中')
        PREPARING_DOCS = 2, _('製作文件中')
        REVIEWING = 3, _('審查中')
        CLOSED = 4, _('結案')
        NOT_PROCESSED = 5, _('沒有辦理')

    class MandateReturn(models.TextChoices):
        DRAFT = 'draft', _('草稿')
        SIGNING = 'signing', _('簽核中')
        APPROVED = 'approved', _('核准')
        REJECTED = 'rejected', _('拒絕')
    
    CASE_TYPE_CHOICES = [
        ('setup', '設立'),
        ('capital_increase', '增資'),
        ('equity_change', '股權異動'),
        ('business_change', '營業人變更'),
    ]

    # 1. Basic Data
    registration_no = models.CharField(_('登記單號'), max_length=20, unique=True, editable=False)
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, null=True)
    company_name = models.CharField(_('公司名稱'), max_length=255)
    line_id = models.CharField(_('Line ID'), max_length=100, blank=True, null=True)
    room_id = models.CharField(_('Room ID'), max_length=100, blank=True, null=True)

    # 2. Contact Data
    main_contact = models.CharField(_('主要聯絡人'), max_length=100, blank=True, null=True)
    mobile = models.CharField(_('手機'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('電話'), max_length=50, blank=True, null=True)
    address = models.CharField(_('通訊地址'), max_length=255, blank=True, null=True)

    # 3. Other
    progress_status = models.IntegerField(_('登記進度'), choices=ProgressStatus.choices, default=ProgressStatus.NEW_CASE)
    mandate_return = models.CharField(_('委任書簽回'), max_length=20, choices=MandateReturn.choices, default=MandateReturn.DRAFT)
    acceptance_date = models.DateField(_('承接日期'), default=timezone.now)
    # Using JSONField for multiple selection as we are on Postgres
    case_type = models.JSONField(_('案件種類'), default=list, blank=True)
    
    # 4. Note
    note = models.TextField(_('備註'), blank=True, null=True)
    quotation_data = models.JSONField(_('報價單資料'), default=list, blank=True)
    cost_sharing_data = models.JSONField(_('公費分攤資料'), default=list, blank=True)

    # 5. Third-party Payment
    payment_token = models.UUIDField(_('支付連結Token'), unique=True, null=True, blank=True)
    payment_status = models.CharField(_('支付狀態'), max_length=20, default='pending', choices=[('pending', '待付款'), ('paid', '已付款'), ('failed', '失敗')])
    
    # Recipient Info
    recipient_name = models.CharField(_('收件人姓名'), max_length=100, blank=True)
    recipient_phone = models.CharField(_('收件人電話'), max_length=50, blank=True)
    recipient_addr = models.CharField(_('收件地址'), max_length=255, blank=True)
    pickup_method = models.CharField(_('取件方式'), max_length=20, default='mail', choices=[('mail', '郵寄'), ('self', '自取')])
    
    is_ar_transferred = models.BooleanField(_('已拋轉應收帳款'), default=False)
    is_posted = models.BooleanField(_('已拋轉傳票過帳'), default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('登記進度表')
        verbose_name_plural = _('登記進度表')
        ordering = ['-registration_no']

    def __str__(self):
        return f"{self.registration_no} - {self.company_name}"

    def to_ar_data(self):
        """Standardized format for AR transfer service."""
        return {
            'company_name': self.company_name,
            'unified_business_no': self.unified_business_no,
            'main_contact': self.main_contact,
            'mobile': self.mobile,
            'phone': self.phone,
            'address': self.address,
            'line_id': self.line_id,
            'room_id': self.room_id,
            'quotation_data': self.quotation_data,
            'cost_sharing_data': self.cost_sharing_data,
            'remarks': self.note
        }

    def save(self, *args, **kwargs):
        if not self.registration_no:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"RO{today_str}"
            # Find last registration number for today
            last_obj = Progress.objects.filter(registration_no__startswith=prefix).order_by('-registration_no').first()
            if last_obj:
                try:
                    last_seq = int(last_obj.registration_no[-3:]) # Get last 3 digits
                    new_seq = last_seq + 1
                except ValueError:
                    new_seq = 1
            else:
                new_seq = 1
            
            self.registration_no = f"{prefix}{new_seq:03d}"
        
            self.registration_no = f"{prefix}{new_seq:03d}"
        
        super().save(*args, **kwargs)

    def generate_payment_token(self):
        if not self.payment_token:
            self.payment_token = uuid.uuid4()
            self.save(update_fields=['payment_token'])
        return self.payment_token
