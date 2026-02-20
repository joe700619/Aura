"""
Workflow Template Models
定義工作流程模板和步驟
"""
from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings


class WorkflowTemplate(models.Model):
    """工作流程模板"""
    
    name = models.CharField("流程名稱", max_length=100)
    code = models.CharField("流程代碼", max_length=50, unique=True,
                           help_text="唯一識別碼，用於程式中引用此流程")
    description = models.TextField("說明", blank=True)
    
    # 提醒設定
    reminder_hours = models.IntegerField("提醒間隔(小時)", default=24,
                                        help_text="多久提醒一次未處理的核准")
    max_reminders = models.IntegerField("最多提醒次數", default=3)
    
    is_active = models.BooleanField("啟用", default=True)
    
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)
    
    class Meta:
        verbose_name = "工作流程模板"
        verbose_name_plural = "工作流程模板"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class WorkflowStep(models.Model):
    """流程步驟"""
    
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name="所屬流程"
    )
    
    step_number = models.IntegerField("步驟順序",
                                     help_text="從1開始，數字越小越先執行")
    step_name = models.CharField("步驟名稱", max_length=100,
                                help_text="例如：HR主管核准、總經理核准")
    
    # 核准者設定（三選一）
    approver_role = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="核准角色",
        help_text="指定群組，該群組的所有成員都可以核准"
    )
    
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_steps_as_approver',
        verbose_name="指定人員",
        help_text="指定特定使用者"
    )
    
    approver_field = models.CharField(
        "動態欄位",
        max_length=100,
        blank=True,
        help_text="從申請物件中動態取得核准者，例如：direct_supervisor"
    )
    
    # 動作權限
    can_approve = models.BooleanField("可核准", default=True)
    can_reject = models.BooleanField("可拒絕", default=True)
    can_return = models.BooleanField("可退回", default=True)
    
    class Meta:
        verbose_name = "流程步驟"
        verbose_name_plural = "流程步驟"
        ordering = ['template', 'step_number']
        unique_together = [['template', 'step_number']]
    
    def __str__(self):
        return f"{self.template.name} - 步驟{self.step_number}: {self.step_name}"
    
    def get_approver(self, obj=None):
        """
        取得此步驟的核准者
        
        Args:
            obj: 申請物件，用於動態欄位查詢
            
        Returns:
            User or Group or None
        """
        if self.approver_user:
            return self.approver_user
        
        if self.approver_role:
            return self.approver_role
        
        if self.approver_field and obj:
            # 從申請物件動態取得核准者
            try:
                return getattr(obj, self.approver_field)
            except AttributeError:
                return None
        
        return None
