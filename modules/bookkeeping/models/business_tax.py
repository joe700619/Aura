import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import BaseModel
from .bookkeeping_client import BookkeepingClient


def get_vat_document_path(instance, filename):
    """
    動態產生營業稅申報書的儲存路徑。
    格式: vat/documents/{tax_id}/{year}/{period_start_month}/{uuid}{ext}
    
    [未來上雲端 (AWS S3) 的註解備忘錄]
    1. 當未來決定將檔案移轉至雲端時，這段程式碼 "完全不需要" 修改。
    2. 您只需要安裝 `pip install django-storages boto3`
    3. 並且在 settings.py 中設定:
       DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
       AWS_ACCESS_KEY_ID = '您的金鑰'
       AWS_SECRET_ACCESS_KEY = '您的密碼'
       AWS_STORAGE_BUCKET_NAME = '您的-bucket-名稱'
    4. Django 接到上傳檔案時，就會自動套用這個路徑結構，把檔案儲存到 S3 中對應的資料夾。
    """
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    
    # 預防客戶無統編的極端狀況
    tax_id = instance.year_record.client.tax_id or 'unknown_client'
    year = instance.year_record.year
    period = instance.period_start_month
    
    return f'vat/documents/{tax_id}/{year}/{period}/{new_filename}'


def get_vat_media_path(instance, filename):
    """
    動態產生營業稅媒體檔的儲存路徑。
    (上雲端設定請參考 get_vat_document_path 的註解)
    """
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    
    tax_id = instance.year_record.client.tax_id or 'unknown_client'
    year = instance.year_record.year
    period = instance.period_start_month
    
    return f'vat/media/{tax_id}/{year}/{period}/{new_filename}'


class TaxFilingSetting(BaseModel):
    """營業稅申報設定 - 第一層 (靜態設定表)"""
    client = models.OneToOneField(
        BookkeepingClient, 
        on_delete=models.CASCADE, 
        related_name='tax_setting',
        verbose_name=_('客戶')
    )
    
    class FormType(models.TextChoices):
        FORM_401 = '401', '401表 (一般稅額計算)'
        FORM_403 = '403', '403表 (兼營營業人)'
        FORM_404 = '404', '404表 (特種稅額計算)'

    class NotificationMethod(models.TextChoices):
        LINE = 'line', 'Line'
        EMAIL = 'email', 'Email'
        BOTH = 'both', 'Line + Email'

    class PaymentMethod(models.TextChoices):
        SELF_PAY = 'self_pay', '自行繳納'
        OFFICE_PAY = 'office_pay', '事務所代繳'
        AUTO_DEBIT = 'auto_debit', '自動扣款'

    class FilingFrequency(models.TextChoices):
        BIMONTHLY = 'bimonthly', '單月申報 (每兩個月)'
        MONTHLY = 'monthly', '按月申報 (每一個月)'
        
    form_type = models.CharField(
        _('申報格式'), 
        max_length=10, 
        choices=FormType.choices, 
        default=FormType.FORM_401
    )
    filing_frequency = models.CharField(
        _('申報頻率'), 
        max_length=20, 
        choices=FilingFrequency.choices, 
        default=FilingFrequency.BIMONTHLY
    )
    is_audited = models.BooleanField(
        _('查帳申報'), 
        default=False,
        help_text=_('打勾代表此客戶後續營所稅或相關申報為查帳申報')
    )
    notification_method = models.CharField(
        _('通知方式'), max_length=10,
        choices=NotificationMethod.choices,
        blank=True, null=True
    )
    payment_method = models.CharField(
        _('預設繳稅方式'), max_length=20,
        choices=PaymentMethod.choices,
        blank=True, null=True
    )
    
    class Meta:
        verbose_name = _('營業稅申報設定')
        verbose_name_plural = _('營業稅申報設定')

    def __str__(self):
        return f"{self.client.name} - 稅務設定"


class TaxFilingYear(BaseModel):
    """申報年度/期別主表 - 第二層 (年度籃子)"""
    client = models.ForeignKey(
        BookkeepingClient, 
        on_delete=models.CASCADE, 
        related_name='tax_years',
        verbose_name=_('客戶')
    )
    year = models.PositiveIntegerField(_('年度(民國)'))
    
    class Meta:
        verbose_name = _('營業稅申報年度')
        verbose_name_plural = _('營業稅申報年度')
        unique_together = ('client', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"{self.client.name} - {self.year}年度"


class TaxFilingPeriod(BaseModel):
    """營業稅申報明細表 - 第三層 (各期數據)"""
    year_record = models.ForeignKey(
        TaxFilingYear, 
        on_delete=models.CASCADE, 
        related_name='periods',
        verbose_name=_('所屬年度')
    )
    
    # 期別：例如 1, 3, 5, 7, 9, 11 (代表單月申報的起月)
    period_start_month = models.PositiveIntegerField(
        _('期別(起月)'),
        help_text=_('例如填寫1代表1-2月期，填寫3代表3-4月期')
    )

    class PeriodPaymentMethod(models.TextChoices):
        SELF_PAY = 'self_pay', '自行繳納'
        OFFICE_PAY = 'office_pay', '事務所代繳'
        AUTO_DEBIT = 'auto_debit', '自動扣繳'
        NO_PAYMENT = 'no_payment', '不用繳納'

    class FilingStatus(models.TextChoices):
        NOT_NOTIFIED = 'not_notified', '尚未通知'
        WAITING = 'waiting', '等待回覆'
        AUTO_REPLIED = 'auto_replied', '自動回覆'
        MANUALLY_REPLIED = 'manually_replied', '人工回覆'
        PAID = 'paid', '繳納完成'
        NO_PAYMENT_NEEDED = 'no_payment_needed', '無須繳納'

    class ReplyMethod(models.TextChoices):
        AUTO = 'auto', '自動回覆'
        MANUAL = 'manual', '人工回覆'
    
    # ── 發票作業 ──
    invoice_received_date = models.DateField(_('收到發票日期'), null=True, blank=True)

    # ── 申報數字 ──
    sales_amount = models.DecimalField(_('銷售額'), max_digits=15, decimal_places=0, default=0)
    tax_amount = models.DecimalField(_('銷項稅額'), max_digits=15, decimal_places=0, default=0)
    input_amount = models.DecimalField(_('進項金額'), max_digits=15, decimal_places=0, default=0)
    input_tax = models.DecimalField(_('進項稅額'), max_digits=15, decimal_places=0, default=0)
    retained_tax = models.DecimalField(_('留抵稅額'), max_digits=15, decimal_places=0, default=0)
    payable_tax = models.DecimalField(_('應納(退)稅額'), max_digits=15, decimal_places=0, default=0)

    # ── 文件上傳 ──
    filing_document = models.FileField(
        _('申報書及稅單'), upload_to=get_vat_document_path, blank=True, null=True
    )
    media_file = models.FileField(
        _('媒體檔'), upload_to=get_vat_media_path, blank=True, null=True
    )

    # ── 申報狀態 ──
    is_filed = models.BooleanField(_('是否已申報'), default=False)
    filing_date = models.DateField(_('申報日期'), null=True, blank=True)

    # ── 繳稅作業 ──
    tax_deadline = models.DateField(_('繳稅截止日'), null=True, blank=True)
    period_payment_method = models.CharField(
        _('繳稅方式'), max_length=20,
        choices=PeriodPaymentMethod.choices,
        blank=True, null=True
    )
    filing_status = models.CharField(
        _('繳納狀態'), max_length=20,
        choices=FilingStatus.choices,
        default=FilingStatus.NOT_NOTIFIED
    )
    reply_time = models.DateTimeField(_('回覆時間'), null=True, blank=True)
    reply_method = models.CharField(
        _('回覆方式'), max_length=10,
        choices=ReplyMethod.choices,
        blank=True, null=True
    )
    # ── 確認連結 Token (不需登入即可回覆) ──
    confirm_token = models.UUIDField(
        _('確認Token'), default=uuid.uuid4, unique=True, editable=False
    )
    
    class Meta:
        verbose_name = _('營業稅申報明細')
        verbose_name_plural = _('營業稅申報明細')
        unique_together = ('year_record', 'period_start_month')
        ordering = ['year_record__year', 'period_start_month']

    def __str__(self):
        return f"{self.year_record} - 第 {self.period_start_month} 期"

    @property
    def period_label(self):
        """回傳 '01-02月' 這樣的字串"""
        freq = self.year_record.client.tax_setting.filing_frequency if hasattr(self.year_record.client, 'tax_setting') else 'bimonthly'
        if freq == 'bimonthly':
            return f"{self.period_start_month:02d}-{self.period_start_month+1:02d}月"
        return f"{self.period_start_month:02d}月"

    # ── 以下 property 是供核心通知系統用的收件人解析入口 ──
    # 通知系統會嘗試 getattr(obj, 'email') / getattr(obj, 'line_id')，
    # TaxFilingPeriod 本身沒有這些欄位，所以透過 property 轉向客戶資料。
    @property
    def email(self):
        """代理：讀取關聯客戶的 Email，供批次 Email 通知使用"""
        return getattr(self.year_record.client, 'email', None)

    @property
    def line_id(self):
        """代理：讀取關聯客戶的 Line ID，供批次 Line 通知使用"""
        return getattr(self.year_record.client, 'line_id', None)

    @property
    def room_id(self):
        """代理：讀取關聯客戶的 Line Room ID，供 Line 群組通知使用"""
        return getattr(self.year_record.client, 'room_id', None)


# ── Signals ──
@receiver(post_save, sender=BookkeepingClient)
def auto_create_tax_filing_setting(sender, instance, created, **kwargs):
    """
    當新增 BookkeepingClient 且 service_type 是需要報營業稅時，
    自動建立其對應的第一層 TaxFilingSetting 表。
    """
    if created:
        needs_vat = [
            BookkeepingClient.ServiceType.VAT_BUSINESS,
            BookkeepingClient.ServiceType.MIXED_DIRECT,
            BookkeepingClient.ServiceType.MIXED_RATIO,
        ]
        if instance.service_type in needs_vat:
            form_type = TaxFilingSetting.FormType.FORM_401
            if instance.service_type in [BookkeepingClient.ServiceType.MIXED_DIRECT, BookkeepingClient.ServiceType.MIXED_RATIO]:
                form_type = TaxFilingSetting.FormType.FORM_403
                
            TaxFilingSetting.objects.create(
                client=instance,
                form_type=form_type
            )
