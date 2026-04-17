from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import BaseModel
from modules.basic_data.models import Customer


class BookkeepingClient(BaseModel):
    """記帳客戶基本資料"""

    class AcceptanceStatus(models.TextChoices):
        ACTIVE = 'active', '承接中'
        SUSPENDED = 'suspended', '停業中'
        TRANSFERRED = 'transferred', '轉出/解散'

    class BillingStatus(models.TextChoices):
        BILLING = 'billing', '收費中'
        STOPPED = 'stopped', '停止收費'

    class ServiceType(models.TextChoices):
        VAT_BUSINESS = 'vat_business', '營業人'
        MIXED_DIRECT = 'mixed_direct', '兼營營業人(直扣法)'
        MIXED_RATIO = 'mixed_ratio', '兼營營業人(比例扣抵)'
        INVESTMENT = 'investment', '專營投資公司'
        PROFESSIONAL = 'professional', '執行業務'
        OTHER = 'other', '其他'

    class SendInvoiceMethod(models.TextChoices):
        POST = 'post', '郵寄'
        IN_PERSON = 'in_person', '親送'
        KEEP = 'keep', '自留'
        MERGE = 'merge', '併同其他客戶'
        CLIENT_PICKUP = 'client_pickup', '客戶自己拿來'
        OTHER = 'other', '其他'

    class ReceiveInvoiceMethod(models.TextChoices):
        SEVEN_ELEVEN = '711_bag', '7-11便利袋'
        CLIENT_POST = 'client_post', '客戶自己寄送來'
        IN_PERSON = 'in_person', '親收'
        MERGE = 'merge', '併同其他客戶'
        COURIER = 'courier', '快遞'
        OTHER = 'other', '其他'
        
    class ClientSource(models.TextChoices):
        OUR_FIRM = 'our_firm', '本所設立'
        TRANSFERRED = 'transferred', '他所轉入'

    # ── 基本資料 ──
    user = models.OneToOneField(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='bookkeeping_client_profile',
        verbose_name=_('綁定帳號'),
        help_text=_('綁定供外部客戶登入的帳號')
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='bookkeeping_clients',
        verbose_name=_('關聯客戶'),
    )
    tax_id = models.CharField(_('統一編號'), max_length=20, blank=True, null=True)
    tax_registration_no = models.CharField(_('稅籍編號'), max_length=20, blank=True, null=True)
    name = models.CharField(_('公司名稱'), max_length=100)
    line_id = models.CharField(_('Line ID'), max_length=50, blank=True, null=True)
    room_id = models.CharField(_('Room ID'), max_length=50, blank=True, null=True)

    # ── 主要聯絡資訊 ──
    contact_person = models.CharField(_('聯絡人'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('電話'), max_length=20, blank=True, null=True)
    mobile = models.CharField(_('手機'), max_length=20, blank=True, null=True)
    email = models.EmailField(_('Email'), blank=True, null=True)
    correspondence_address = models.CharField(_('通訊地址'), max_length=255, blank=True, null=True)
    registered_address = models.CharField(_('登記地址'), max_length=255, blank=True, null=True)

    # ── 其他資料 ──
    acceptance_status = models.CharField(
        _('承接狀態'), max_length=20,
        choices=AcceptanceStatus.choices,
        default=AcceptanceStatus.ACTIVE,
    )
    billing_status = models.CharField(
        _('計費狀態'), max_length=20,
        choices=BillingStatus.choices,
        default=BillingStatus.BILLING,
    )
    service_type = models.CharField(
        _('提供服務'), max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.VAT_BUSINESS,
    )
    group_assistant = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bookkeeping_group_clients',
        verbose_name=_('集團助理'),
    )
    bookkeeping_assistant = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bookkeeping_assistant_clients',
        verbose_name=_('記帳助理'),
    )

    # ── 備註 ──
    notes = models.TextField(_('備註'), blank=True, null=True)

    # ── 統購發票 - 發票提供方式 ──
    has_group_invoice = models.BooleanField(_('是否統購發票'), default=False)

    send_invoice_method = models.CharField(
        _('送發票方式'), max_length=20,
        choices=SendInvoiceMethod.choices,
        blank=True, null=True
    )
    send_merged_client_name = models.CharField(
        _('併同客戶名稱 (送發票)'), max_length=100, blank=True, null=True
    )

    # ── 統購發票 - 發票收回方式 ──
    receive_invoice_method = models.CharField(
        _('收發票方式'), max_length=20,
        choices=ReceiveInvoiceMethod.choices,
        blank=True, null=True
    )
    receive_merged_client_name = models.CharField(
        _('併同客戶名稱 (收發票)'), max_length=100, blank=True, null=True
    )

    # ── 客戶來源與移交 ──
    client_source = models.CharField(
        _('客戶來源'), max_length=20,
        choices=ClientSource.choices,
        blank=True, null=True
    )
    contact_date = models.DateField(
        _('聯繫客戶日期'), blank=True, null=True
    )
    transfer_checklist = models.JSONField(
        _('移交檢查表'), default=dict, blank=True
    )

    # ── 7-11 便利袋追蹤 ──
    last_convenience_bag_date = models.DateField(
        _('最後提供便利袋日期'), blank=True, null=True
    )
    last_convenience_bag_qty = models.PositiveIntegerField(
        _('最後提供便利袋數量'), blank=True, null=True
    )

    # ── 帳號密碼 (營業人) ──
    business_password = models.CharField(
        _('記帳客戶登入密碼'), max_length=100, blank=True, null=True
    )
    national_tax_password = models.CharField(
        _('營業人(國稅局)密碼'), max_length=100, blank=True, null=True
    )
    e_invoice_account = models.CharField(
        _('電子發票帳號'), max_length=100, blank=True, null=True
    )
    e_invoice_password = models.CharField(
        _('電子發票密碼'), max_length=100, blank=True, null=True
    )

    # ── 公費分攤 ──
    cost_sharing_data = models.JSONField(_('公費分攤資料'), default=list, blank=True)

    class Meta:
        verbose_name = _('記帳客戶')
        verbose_name_plural = _('記帳客戶')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tax_id'],
                condition=Q(is_deleted=False) & Q(tax_id__isnull=False) & ~Q(tax_id=''),
                name='unique_active_bookkeeping_client_tax_id',
            )
        ]

    def __str__(self):
        return self.name

    @property
    def active_service_fee(self):
        """返回目前生效中的服務費用記錄"""
        today = timezone.now().date()
        return self.service_fees.filter(
            effective_date__lte=today,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).order_by('-effective_date').first()
