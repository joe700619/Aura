"""
Approver Delegate Model
定義代理人設定
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from .template import WorkflowTemplate


class ApproverDelegate(models.Model):
    """代理人設定"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations',
        verbose_name="原核准者"
    )
    
    delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegated_approvals',
        verbose_name="代理人"
    )
    
    start_date = models.DateField("代理開始日期")
    end_date = models.DateField("代理結束日期")
    
    workflow_template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="限定流程",
        help_text="留空表示適用所有流程"
    )
    
    is_active = models.BooleanField("啟用", default=True)
    
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    
    class Meta:
        verbose_name = "代理人設定"
        verbose_name_plural = "代理人管理"
        ordering = ['-start_date']
    
    def __str__(self):
        template_str = f" ({self.workflow_template.name})" if self.workflow_template else " (所有流程)"
        return f"{self.user.get_full_name()} → {self.delegate.get_full_name()}{template_str}"
    
    def is_valid_now(self):
        """檢查代理設定是否在有效期間內"""
        today = timezone.now().date()
        return (
            self.is_active and
            self.start_date <= today <= self.end_date
        )
    
    def clean(self):
        """驗證邏輯"""
        from django.core.exceptions import ValidationError
        
        # 不能代理給自己
        # 不能代理給自己
        if self.user_id and self.delegate_id and self.user_id == self.delegate_id:
            raise ValidationError("不能設定自己為代理人")
        
        # 開始日期不能晚於結束日期
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("開始日期不能晚於結束日期")
