import os
from django.db import models
from django.utils import timezone
from core.models import BaseModel
from modules.basic_data.models.customer import Customer
from django.contrib.auth import get_user_model

User = get_user_model()

class IrsAuditNotice(BaseModel):
    TAX_CATEGORY_CHOICES = [
        ('營業稅', '營業稅'),
        ('所得稅', '所得稅'),
        ('印花稅', '印花稅'),
        ('個人綜所', '個人綜所'),
        ('遺贈稅', '遺贈稅'),
        ('貨物稅', '貨物稅'),
        ('其他', '其他'),
    ]
    STATUS_CHOICES = [
        ('待處理', '待處理'),
        ('處理中', '處理中'),
        ('已結案', '已結案'),
    ]

    # Card 1: 主要資訊 (Main Info)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="客戶")
    tax_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="統一編號") # Add JS auto-fill
    attributable_year = models.IntegerField(blank=True, null=True, verbose_name="歸屬年度")
    tax_category = models.CharField(max_length=50, choices=TAX_CATEGORY_CHOICES, blank=True, null=True, verbose_name="稅種分類")
    subject = models.CharField(max_length=255, verbose_name="信件主旨")
    receipt_date = models.DateField(default=timezone.now, verbose_name="收文日期")
    assigned_assistant = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_audit_notices', verbose_name="指派助理")
    assistant_email = models.EmailField(blank=True, null=True, verbose_name="助理Email")

    # Card 2: 狀態與附件 (Status & Attachments)
    reply_deadline = models.DateField(blank=True, null=True, verbose_name="回復截止日")
    merge_annual_income_tax = models.BooleanField(default=False, verbose_name="併入年度所得稅處理事項")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='待處理', verbose_name="處理狀態")
    attachment = models.FileField(upload_to='irs_audit_notices/%Y/%m/', blank=True, null=True, verbose_name="附件上傳")
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")

    # Card 3: 國稅局資料 (IRS Data)
    irs_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="電話")
    irs_contact = models.CharField(max_length=100, blank=True, null=True, verbose_name="聯絡人")
    irs_email = models.EmailField(blank=True, null=True, verbose_name="Email")
    irs_district = models.CharField(max_length=100, blank=True, null=True, verbose_name="國稅局轄區")

    class Meta:
        verbose_name = "國稅局查帳通知"
        verbose_name_plural = "國稅局查帳通知"
        ordering = ['-receipt_date', '-created_at']

    def __str__(self):
        return f"{self.customer} - {self.subject} ({self.receipt_date})"

    # Approval Workflow Helper Methods (Copied from CaseAssessment style)
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
        """檢查使用者是否可以核准此案件"""
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

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('administrative:irs_audit_notice_update', kwargs={'pk': self.pk})


class IrsAuditNoticeAttachment(models.Model):
    notice = models.ForeignKey(IrsAuditNotice, on_delete=models.CASCADE, related_name='attachments', verbose_name="查帳通知")
    file = models.FileField(upload_to='irs_audit_notices/%Y/%m/', verbose_name="附件")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上傳時間")

    class Meta:
        verbose_name = "查帳通知附件"
        verbose_name_plural = "查帳通知附件"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.notice} - {os.path.basename(self.file.name)}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def is_image(self):
        return self.file.name.lower().rsplit('.', 1)[-1] in ('jpg', 'jpeg', 'png', 'gif', 'webp')


class IrsAuditCommunication(BaseModel):
    notice = models.ForeignKey(IrsAuditNotice, on_delete=models.CASCADE, related_name='communications', verbose_name="查帳通知")
    comm_time = models.DateTimeField(default=timezone.now, verbose_name="時間")
    comm_content = models.TextField(verbose_name="溝通內容")
    reply_status = models.CharField(max_length=100, blank=True, null=True, verbose_name="回復狀態")

    class Meta:
        verbose_name = "國稅局溝通紀錄"
        verbose_name_plural = "國稅局溝通紀錄"
        ordering = ['-comm_time']

    def __str__(self):
        return f"{self.notice} - {self.comm_time}"
