from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class LeaveType(BaseModel):
    """
    假別設定
    定義各種假別的名稱、是否有薪、年度上限等。
    """

    code = models.CharField(_('假別代碼'), max_length=30, unique=True)
    name = models.CharField(_('假別名稱'), max_length=50)
    is_paid = models.BooleanField(_('有薪假'), default=True)
    max_hours_per_year = models.DecimalField(
        _('年度上限(小時)'),
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text=_('留空代表無上限或由人工給予'),
    )
    requires_doc = models.BooleanField(
        _('需附證明'),
        default=False,
        help_text=_('是否需要上傳附件/證明文件'),
    )
    description = models.TextField(_('說明'), blank=True, default='')
    sort_order = models.IntegerField(_('排序'), default=0)

    class Meta:
        ordering = ['sort_order', 'code']
        verbose_name = _('假別設定')
        verbose_name_plural = _('假別設定')

    def __str__(self):
        return self.name


class LeaveBalance(BaseModel):
    """
    假期餘額
    記錄每位員工每年各假別的應有時數與已使用時數。
    """

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='leave_balances',
        verbose_name=_('員工'),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances',
        verbose_name=_('假別'),
    )
    year = models.IntegerField(_('年度'))
    period_start = models.DateField(
        _('生效日'),
        null=True,
        blank=True,
        help_text=_('假期有效起始日'),
    )
    period_end = models.DateField(
        _('到期日'),
        null=True,
        blank=True,
        help_text=_('假期有效截止日'),
    )
    entitled_hours = models.DecimalField(
        _('應有時數'),
        max_digits=6,
        decimal_places=1,
        default=0,
    )
    used_hours = models.DecimalField(
        _('已使用時數'),
        max_digits=6,
        decimal_places=1,
        default=0,
    )
    manually_granted = models.BooleanField(
        _('人工給假'),
        default=False,
        help_text=_('如喪假等由管理員手動給予'),
    )
    
    # Deferred Leave Tracking Flags
    is_carried_over = models.BooleanField(
        _('已結轉遞延'),
        default=False,
        help_text=_('是否已將未用完的天數結轉為下一年度的遞延特休'),
    )
    is_settled = models.BooleanField(
        _('已折算薪資'),
        default=False,
        help_text=_('是否已將到期未用完的遞延特休折算為薪資'),
    )

    class Meta:
        ordering = ['employee', 'leave_type']
        verbose_name = _('假期餘額')
        verbose_name_plural = _('假期餘額')
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'leave_type', 'year', 'period_start'],
                name='unique_employee_leave_period',
            )
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type.name} ({self.year})"

    @property
    def remaining_hours(self):
        return self.entitled_hours - self.used_hours


class LeaveSettlementRecord(BaseModel):
    """
    特休折算薪資紀錄
    當遞延特休到期仍未休完時，自動計算並產生此紀錄，後續併入薪資單發放。
    """
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='leave_settlements',
        verbose_name=_('員工'),
    )
    leave_balance = models.OneToOneField(
        LeaveBalance,
        on_delete=models.CASCADE,
        related_name='settlement_record',
        verbose_name=_('來源假期餘額'),
    )
    payroll_record = models.ForeignKey(
        'hr.PayrollRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_settlements',
        verbose_name=_('發放於哪期薪資單'),
        help_text=_('綁定薪資單，確認已發放'),
    )
    date_settled = models.DateField(
        _('結算日期'),
        auto_now_add=True,
    )
    hours = models.DecimalField(
        _('折算時數'),
        max_digits=6,
        decimal_places=1,
    )
    hourly_rate = models.DecimalField(
        _('時薪'),
        max_digits=10,
        decimal_places=0,
        help_text=_('結算當時的時薪'),
    )
    total_amount = models.DecimalField(
        _('折算金額'),
        max_digits=10,
        decimal_places=0,
    )

    class Meta:
        ordering = ['-date_settled']
        verbose_name = _('特休折算紀錄')
        verbose_name_plural = _('特休折算紀錄')

    def __str__(self):
        return f"{self.employee.name} - {self.hours}h ({self.total_amount})"


class LeaveRequest(BaseModel):
    """
    請假單
    員工請假申請，包含假別、起訖日期時間、時數等。
    """

    STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '已核准'),
        ('rejected', '已駁回'),
        ('cancelled', '已取消'),
    ]

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests',
        verbose_name=_('員工'),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name=_('假別'),
    )
    start_datetime = models.DateTimeField(_('開始時間'))
    end_datetime = models.DateTimeField(_('結束時間'))
    total_hours = models.DecimalField(
        _('請假時數'),
        max_digits=6,
        decimal_places=1,
    )
    reason = models.TextField(_('請假事由'))
    status = models.CharField(
        _('狀態'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves',
        verbose_name=_('核准人'),
    )
    attachment = models.FileField(
        _('附件'),
        upload_to='leave_attachments/%Y/%m/',
        null=True,
        blank=True,
    )
    note = models.TextField(_('備註'), blank=True, default='')

    class Meta:
        ordering = ['-start_datetime']
        verbose_name = _('請假單')
        verbose_name_plural = _('請假單')

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type.name} ({self.total_hours}h)"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hr:leave_request_update', kwargs={'pk': self.pk})

    # ========== Approval Workflow Helper Methods ==========

    def get_approval_request(self):
        """取得當前的核准請求"""
        from modules.workflow.services import get_approval_request
        return get_approval_request(self)

    def can_submit_for_approval(self):
        """是否可以送出核准"""
        approval = self.get_approval_request()
        if not approval:
            return True
        return approval.status in ['DRAFT', 'RETURNED']

    def can_user_approve(self, user):
        """檢查使用者是否可以核准此請假單"""
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
        """檢查使用者是否可以撤回"""
        approval = self.get_approval_request()
        if not approval:
            return False
        return approval.requester == user and approval.status in ['PENDING', 'RETURNED']

    def cancel(self):
        """取消請假並回沖餘額"""
        if self.status in ('pending', 'approved'):
            self.status = 'cancelled'
            self.save(update_fields=['status'])
            
            # 回沖餘額 based on the active period covering the start date
            start_date = self.start_datetime.date()
            balance = LeaveBalance.objects.filter(
                employee=self.employee,
                leave_type=self.leave_type,
                period_start__lte=start_date,
                period_end__gt=start_date,
            ).first()
            
            if not balance:
                # Fallback
                balance = LeaveBalance.objects.filter(
                    employee=self.employee,
                    leave_type=self.leave_type,
                    year=self.start_datetime.year,
                ).first()
                
            if balance:
                balance.used_hours -= self.total_hours
                if balance.used_hours < 0:
                    balance.used_hours = 0
                balance.save(update_fields=['used_hours'])
