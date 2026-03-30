from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import BaseModel

class AdvancePayment(BaseModel):
    advance_no = models.CharField(_('代墊款單號'), max_length=50, unique=True, blank=True)
    date = models.DateField(_('日期'), default=timezone.now)
    applicant = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, verbose_name=_('申請人'))
    total_amount = models.DecimalField(_('金額合計'), max_digits=12, decimal_places=0, default=0)
    description = models.TextField(_('摘要'), blank=True, null=True)
    note = models.TextField(_('備註'), blank=True, null=True)
    
    # Voucher posting check
    is_posted = models.BooleanField(_('已拋轉傳票'), default=False)
    
    class Meta:
        verbose_name = _('代墊款')
        verbose_name_plural = _('代墊款')
        ordering = ['-date', '-advance_no']

    def __str__(self):
        return self.advance_no or f"代墊款 ({self.date})"
        
    def get_approval_request(self):
        from modules.workflow.services import get_approval_request
        return get_approval_request(self)
    
    def can_submit_for_approval(self):
        approval = self.get_approval_request()
        if not approval:
            return True
        return approval.status in ['DRAFT', 'RETURNED']
    
    def can_user_approve(self, user):
        from modules.workflow.services import get_effective_approver
        approval = self.get_approval_request()
        if not approval or approval.status != 'PENDING':
            return False
        if not approval.current_step:
            return False
        step_approver = approval.current_step.get_approver(self)
        if not step_approver:
            return False
        from django.contrib.auth.models import Group
        if isinstance(step_approver, Group):
            if user.groups.filter(id=step_approver.id).exists():
                return True
            effective_approver, _ = get_effective_approver(user, approval)
            return effective_approver != user
        else:
            effective_approver, original = get_effective_approver(step_approver, approval)
            return effective_approver == user
    
    def can_user_cancel(self, user):
        approval = self.get_approval_request()
        if not approval:
            return False
        return approval.requester == user and approval.status in ['PENDING', 'RETURNED']

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('administrative:advance_payment_update', kwargs={'pk': self.pk})


class AdvancePaymentDetail(BaseModel):
    class PaymentType(models.TextChoices):
        POSTAGE = 'POSTAGE', _('郵資及快遞')
        GROUP_INVOICE = 'GROUP_INVOICE', _('統購發票')
        TAX = 'TAX', _('稅款')
        SUPPLEMENTARY_PREMIUM = 'SUPPLEMENTARY_PREMIUM', _('補充保費')
        GOV_FEE = 'GOV_FEE', _('政府規費')
        RETAIL_INVOICE = 'RETAIL_INVOICE', _('零買發票')
        SEAL = 'SEAL', _('印章')
        
    advance_payment = models.ForeignKey(AdvancePayment, on_delete=models.CASCADE, related_name='details', verbose_name=_('代墊款主檔'))
    is_customer_absorbed = models.BooleanField(_('客戶吸收'), default=True)
    customer = models.ForeignKey('basic_data.Customer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('費用歸屬'))
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, null=True)
    reason = models.CharField(_('事由'), max_length=255, blank=True, null=True)
    amount = models.DecimalField(_('代墊費用'), max_digits=12, decimal_places=0, default=0)
    is_billed = models.BooleanField(_('是否已發單'), default=False)
    payment_type = models.CharField(_('代墊類型'), max_length=50, choices=PaymentType.choices, blank=True, null=True)
    
    class Meta:
        verbose_name = _('代墊款明細')
        verbose_name_plural = _('代墊款明細')
        ordering = ['created_at']

    def __str__(self):
        if self.reason:
            return f"{self.advance_payment.advance_no} - {self.reason}"
        return f"{self.advance_payment.advance_no} - Detail"


class AdvancePaymentImage(BaseModel):
    advance_payment = models.ForeignKey(AdvancePayment, related_name='images', on_delete=models.CASCADE, verbose_name=_('代墊款'))
    image = models.ImageField(upload_to='advance_payments/%Y/%m/', verbose_name=_('圖片檔案'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('上傳時間'))

    class Meta:
        verbose_name = _('代墊款夾檔圖片')
        verbose_name_plural = _('代墊款夾檔圖片')
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.advance_payment.advance_no} - Image {self.id}"
