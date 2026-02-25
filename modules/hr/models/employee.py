from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class Employee(models.Model):
    """
    員工資料模型
    
    區塊一：基本資料
    區塊二：通訊方式
    區塊三：在職狀態
    """
    
    # ========== 選項定義 ==========
    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', '在職'),
        ('RESIGNED', '離職'),
        ('ON_LEAVE', '留職停薪'),
    ]
    
    TEAM_CHOICES = [
        ('A', 'A組'),
        ('B', 'B組'),
    ]
    
    # ========== 區塊一：基本資料 ==========
    employee_number = models.CharField(
        _("員工編號"),
        max_length=10,
        unique=True,
        editable=False,
        help_text=_("自動生成，格式：西元年+序號（如：2026001）")
    )
    name = models.CharField(_("姓名"), max_length=100)
    gender = models.CharField(_("性別"), max_length=1, choices=GENDER_CHOICES)
    id_number = models.CharField(
        _("身分證字號"),
        max_length=10,
        unique=True,
        help_text=_("身分證字號須為唯一")
    )
    line_id = models.CharField(_("Line ID"), max_length=100, blank=True)
    extension = models.CharField(_("分機號碼"), max_length=10, blank=True)
    
    # ========== 區塊二：通訊方式 ==========
    phone = models.CharField(_("電話"), max_length=20, blank=True)
    address = models.TextField(_("地址"), blank=True)
    email = models.EmailField(_("Email"), blank=True)
    
    # ========== 區塊三：在職狀態 ==========
    employment_status = models.CharField(
        _("在職狀態"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    hire_date = models.DateField(_("到職日期"))
    resignation_date = models.DateField(_("離職日期"), blank=True, null=True)
    team = models.CharField(_("組別"), max_length=1, choices=TEAM_CHOICES)
    
    # ========== 系統欄位 ==========
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)
    updated_at = models.DateTimeField(_("更新時間"), auto_now=True)
    is_active = models.BooleanField(_("啟用狀態"), default=True)
    
    # ========== 帳號關聯 ==========
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='employee_profile',
        verbose_name=_("系統登入帳號"),
        help_text=_("綁定此員工對應的系統登入帳號")
    )
    
    class Meta:
        verbose_name = _("員工")
        verbose_name_plural = _("員工")
        ordering = ['-employee_number']
    
    def __str__(self):
        return f"{self.employee_number} - {self.name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hr:employee_update', kwargs={'pk': self.pk})
    
    # Approval Workflow Helper Methods
    
    def get_approval_request(self):
        """取得當前的核准請求"""
        from modules.workflow.services import get_approval_request
        return get_approval_request(self)
    
    def can_submit_for_approval(self):
        """是否可以送出核准"""
        approval = self.get_approval_request()
        if not approval:
            return True  # 沒有核准請求，可以建立新的
        return approval.status in ['DRAFT', 'RETURNED']
    
    def can_user_approve(self, user):
        """檢查使用者是否可以核准此員工"""
        from modules.workflow.services import get_effective_approver
        
        approval = self.get_approval_request()
        if not approval or approval.status != 'PENDING':
            return False
        
        if not approval.current_step:
            return False
        
        # 取得指定的核准者
        step_approver = approval.current_step.get_approver(self)
        
        if not step_approver:
            return False
        
        # 檢查是否為指定核准者（考慮代理人）
        from django.contrib.auth.models import Group
        if isinstance(step_approver, Group):
            # 檢查使用者是否屬於該群組
            if user.groups.filter(id=step_approver.id).exists():
                return True
            # 檢查是否有人代理該群組成員
            effective_approver, _ = get_effective_approver(user, approval)
            return effective_approver != user
        else:
            # 檢查是否為指定使用者或代理人
            effective_approver, original = get_effective_approver(step_approver, approval)
            return effective_approver == user
    
    def can_user_cancel(self, user):
        """檢查使用者是否可以撤回"""
        approval = self.get_approval_request()
        if not approval:
            return False
        return approval.requester == user and approval.status in ['PENDING', 'RETURNED']

    
    def save(self, *args, **kwargs):
        """
        自動生成員工編號
        格式：西元年 + 三位序號（如：2026001）
        """
        if not self.employee_number:
            current_year = timezone.now().year
            
            # 查詢該年度最後的員工編號
            last_employee = Employee.objects.filter(
                employee_number__startswith=str(current_year)
            ).order_by('-employee_number').first()
            
            if last_employee:
                # 取得最後三位數字並加1
                last_number = int(last_employee.employee_number[-3:])
                new_number = last_number + 1
            else:
                # 該年度第一位員工
                new_number = 1
            
            # 組合員工編號：年份 + 三位數字（補零）
            self.employee_number = f"{current_year}{new_number:03d}"
        
        super().save(*args, **kwargs)
