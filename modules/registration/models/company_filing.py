from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class CompanyFiling(models.Model):
    class FilingMethod(models.TextChoices):
        OFFICE = 'OFFICE', _('本所申報')
        SELF = 'SELF', _('自行申報')

    # 1. Basic Data
    filing_no = models.CharField(_('檔案編號'), max_length=20, unique=True, editable=False)
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
    fee = models.DecimalField(_('費用'), max_digits=12, decimal_places=2, default=0)
    filing_method = models.CharField(_('申報方式'), max_length=20, choices=FilingMethod.choices, default=FilingMethod.OFFICE)
    account = models.CharField(_('帳號'), max_length=100, blank=True, null=True)
    password = models.CharField(_('密碼'), max_length=100, blank=True, null=True)
    health_insurance_card_no = models.CharField(_('健保卡號'), max_length=100, blank=True, null=True)

    # 4. Note
    note = models.TextField(_('備註'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('公司法22-1申報')
        verbose_name_plural = _('公司法22-1申報')
        ordering = ['-filing_no']

    def __str__(self):
        return f"{self.filing_no} - {self.company_name}"

    def save(self, *args, **kwargs):
        if not self.filing_no:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"CF{today_str}"
            last_obj = CompanyFiling.objects.filter(filing_no__startswith=prefix).order_by('-filing_no').first()
            if last_obj:
                try:
                    last_seq = int(last_obj.filing_no[-3:])
                    new_seq = last_seq + 1
                except ValueError:
                    new_seq = 1
            else:
                new_seq = 1
            self.filing_no = f"{prefix}{new_seq:03d}"
        super().save(*args, **kwargs)

class FilingHistory(models.Model):
    class FilingCategory(models.TextChoices):
        CHANGE = 'CHANGE', _('變動申報')
        ANNUAL = 'ANNUAL', _('年度申報')

    company_filing = models.ForeignKey(CompanyFiling, on_delete=models.CASCADE, related_name='histories')
    year = models.IntegerField(_('年度'), default=timezone.now().year)
    category = models.CharField(_('類別'), max_length=10, choices=FilingCategory.choices, default=FilingCategory.ANNUAL)
    filing_date = models.DateField(_('申報日期'), default=timezone.now)
    registration_no = models.CharField(_('登記單號'), max_length=50, blank=True, null=True)
    is_completed = models.BooleanField(_('是否已完成'), default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('申報歷程')
        verbose_name_plural = _('申報歷程')
        ordering = ['-year', '-filing_date']
