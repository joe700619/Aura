from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.models import BaseModel
import json

class Receivable(BaseModel):
    receivable_no = models.CharField(_('應收帳款編號'), max_length=50, blank=True, null=True, unique=True)
    
    # Basic Data (Matches ClientAssessment)
    company_name = models.CharField(_('公司名稱'), max_length=255)
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, null=True)
    line_id = models.CharField(_('Line ID'), max_length=100, blank=True, null=True)
    room_id = models.CharField(_('Room ID'), max_length=100, blank=True, null=True)

    # Contact Data
    main_contact = models.CharField(_('主要聯絡人'), max_length=100, blank=True, null=True)
    mobile = models.CharField(_('手機'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('電話'), max_length=50, blank=True, null=True)
    address = models.CharField(_('通訊地址'), max_length=255, blank=True, null=True)
    email = models.EmailField(_('客戶Email'), blank=True, null=True)

    # Other Info
    assistant = models.CharField(_('記帳助理'), max_length=100, blank=True, null=True)
    assistant_email = models.EmailField(_('助理Email'), blank=True, null=True)
    is_posted = models.BooleanField(_('已過帳'), default=False)
    remarks = models.TextField(_('備註'), blank=True)

    # Component Data (JSON)
    quotation_data = models.JSONField(_('報價單明細'), default=list, blank=True)
    cost_sharing_data = models.JSONField(_('公費分攤'), default=list, blank=True)

    # Generic Linkage (Source of this AR)
    source_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    source_object = GenericForeignKey('source_content_type', 'source_id')

    class Meta:
        verbose_name = _('應收帳款')
        verbose_name_plural = _('應收帳款')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.receivable_no or 'No NO'} - {self.company_name}"

    @property
    def total_amount(self):
        """Sum of all quotation items."""
        try:
            return sum(int(item.get('amount', 0)) for item in self.quotation_data)
        except (TypeError, ValueError):
            return 0

    @property
    def paid_amount(self):
        """Sum of all collections."""
        if not self.pk:
            return 0
        return sum(collection.total for collection in self.collections.all())

    @property
    def outstanding_balance(self):
        """Total - Paid."""
        if not self.pk:
            return self.total_amount
        return self.total_amount - self.paid_amount

    @property
    def aging(self):
        """Current date - created date in days."""
        if not self.created_at:
            return 0
        delta = timezone.now() - self.created_at
        return delta.days

    def get_absolute_url(self):
        return reverse('internal_accounting:receivable_edit', kwargs={'pk': self.pk})

class ReceivableFeeApportion(BaseModel):
    receivable = models.ForeignKey(Receivable, on_delete=models.CASCADE, related_name='fee_apportions', verbose_name=_('應收帳款'))
    employee = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, related_name='fee_apportions', verbose_name=_('員工'))
    task_description = models.CharField(_('執行項目'), max_length=255, blank=True)
    ratio = models.DecimalField(_('分攤比例(%)'), max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(_('分攤金額'), max_digits=12, decimal_places=0, default=0)
    
    class Meta:
        verbose_name = _('公費分攤明細')
        verbose_name_plural = _('公費分攤明細')
        ordering = ['id']

    def __str__(self):
        return f"{self.receivable} - {self.employee} - {self.amount}"
