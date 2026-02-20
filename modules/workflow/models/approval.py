"""
Approval Request and History Models
定義核准請求和歷史記錄
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .template import WorkflowTemplate, WorkflowStep


class ApprovalRequest(models.Model):
    """核准請求 - 使用 GenericForeignKey 適用於任何需要核准的物件"""
    
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('PENDING', '待核准'),
        ('RETURNED', '已退回'),
        ('APPROVED', '已核准'),
        ('REJECTED', '已拒絕'),
        ('CANCELLED', '已撤回'),
    ]
    
    # 通用關聯 - 可以關聯任何 model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="物件類型"
    )
    object_id = models.PositiveIntegerField("物件ID")
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 流程資訊
    workflow_template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.PROTECT,
        verbose_name="工作流程"
    )
    
    current_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="當前步驟"
    )
    
    # 狀態
    status = models.CharField(
        "狀態",
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    # 申請資訊
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='my_approval_requests',
        verbose_name="申請人"
    )
    
    # 時間記錄
    request_date = models.DateTimeField("建立時間", auto_now_add=True)
    submit_date = models.DateTimeField("送出時間", null=True, blank=True)
    completed_date = models.DateTimeField("完成時間", null=True, blank=True)
    
    # 提醒記錄
    last_reminder_sent = models.DateTimeField("最後提醒時間", null=True, blank=True)
    reminder_count = models.IntegerField("已提醒次數", default=0)
    
    class Meta:
        verbose_name = "核准請求"
        verbose_name_plural = "核准請求"
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.content_object} - {self.get_status_display()}"
    
    def get_current_approver(self):
        """取得當前步驟的核准者"""
        if not self.current_step:
            return None
        return self.current_step.get_approver(self.content_object)
    
    def get_next_step(self):
        """取得下一個步驟"""
        # 如果已經完成，沒有下一步
        if self.status in ['APPROVED', 'REJECTED', 'CANCELLED']:
            return None
            
        if not self.current_step:
            # 如果沒有當前步驟，取得第一個步驟
            return self.workflow_template.steps.first()
        
        # 取得下一個步驟
        return self.workflow_template.steps.filter(
            step_number__gt=self.current_step.step_number
        ).first()
    
    def is_final_step(self):
        """判斷是否為最後一步"""
        # 如果已完成，回傳 True
        if self.status in ['APPROVED', 'REJECTED', 'CANCELLED']:
            return True
            
        if not self.current_step:
            return False
        return not self.get_next_step()


class ApprovalHistory(models.Model):
    """核准歷史記錄"""
    
    ACTION_CHOICES = [
        ('SUBMIT', '送出'),
        ('APPROVE', '核准'),
        ('REJECT', '拒絕'),
        ('RETURN', '退回'),
        ('CANCEL', '撤回'),
        ('RESUBMIT', '重新送出'),
    ]
    
    approval_request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="核准請求"
    )
    
    step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="流程步驟"
    )
    
    action = models.CharField(
        "動作",
        max_length=20,
        choices=ACTION_CHOICES
    )
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='approval_actions',
        verbose_name="操作者"
    )
    
    actor_as_delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_delegated_actions',
        verbose_name="代理身分",
        help_text="如果是代理人操作，此欄位記錄原核准者"
    )
    
    action_date = models.DateTimeField("操作時間", auto_now_add=True)
    comments = models.TextField("簽核意見", blank=True)
    
    # 通知記錄
    email_sent = models.BooleanField("Email已發送", default=False)
    line_sent = models.BooleanField("Line已發送", default=False)
    
    class Meta:
        verbose_name = "核准歷史"
        verbose_name_plural = "核准歷史"
        ordering = ['-action_date']
    
    def __str__(self):
        delegate_str = f"(代理{self.actor_as_delegate.get_full_name()})" if self.actor_as_delegate else ""
        return f"{self.actor.get_full_name()}{delegate_str} - {self.get_action_display()}"


class ApprovalReminder(models.Model):
    """提醒記錄"""
    
    approval_request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name="核准請求"
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='approval_reminders_received',
        verbose_name="收件人"
    )
    
    sent_date = models.DateTimeField("發送時間", auto_now_add=True)
    reminder_number = models.IntegerField("第幾次提醒")
    
    email_sent = models.BooleanField("Email已發送", default=False)
    line_sent = models.BooleanField("Line已發送", default=False)
    
    class Meta:
        verbose_name = "提醒記錄"
        verbose_name_plural = "提醒記錄"
        ordering = ['-sent_date']
    
    def __str__(self):
        return f"提醒 {self.recipient.get_full_name()} - 第{self.reminder_number}次"
