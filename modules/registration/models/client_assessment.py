from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation
from modules.workflow.models import ApprovalRequest
from django.urls import reverse

class ClientAssessment(models.Model):
    class RiskLevel(models.IntegerChoices):
        NORMAL = 0, _('一般風險')
        HIGH = 1, _('高風險')

    # Basic Data
    company_name = models.CharField(_('公司名稱'), max_length=255)
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, null=True, unique=True)
    line_id = models.CharField(_('Line ID'), max_length=100, blank=True, null=True)
    room_id = models.CharField(_('Room ID'), max_length=100, blank=True, null=True)

    # Contact Data
    main_contact = models.CharField(_('主要聯絡人'), max_length=100, blank=True, null=True)
    mobile = models.CharField(_('手機'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('電話'), max_length=50, blank=True, null=True)
    address = models.CharField(_('通訊地址'), max_length=255, blank=True, null=True)

    # Other
    risk_level = models.IntegerField(_('風險層級'), choices=RiskLevel.choices, default=RiskLevel.NORMAL)

    # Specific Situation Assessment
    # a.是否為我國政府機關及公營事業機構。
    is_gov_agency = models.BooleanField(_('是否為我國政府機關及公營事業機構'), default=False)
    # b.是否為外國政府機關。
    is_foreign_gov = models.BooleanField(_('是否為外國政府機關'), default=False)
    # c.是否為我國公開發行公司及其子公司。
    is_public_company = models.BooleanField(_('是否為我國公開發行公司及其子公司'), default=False)
    # d.是否為於國外掛牌並依掛牌所在地規定，應揭露其主要股東之股票上市、上櫃公司其子公司。
    is_foreign_listed_subsidiary = models.BooleanField(
        _('是否為於國外掛牌並依掛牌所在地規定，應揭露其主要股東之股票上市、上櫃公司其子公司'), default=False
    )
    # e.是否為受我國監理之金融機構及其管理之投資工具。
    is_regulated_financial_inst = models.BooleanField(
        _('是否為受我國監理之金融機構及其管理之投資工具'), default=False
    )
    # f.是否設立於我國境外，且所受監理規範與防制洗錢金融行動工作組織（FATF）所定防制洗錢及打擊資恐標準一致之金融機構，及該金融機構管理之投資工具。
    is_foreign_regulated_inst = models.BooleanField(
        _('是否設立於我國境外，且所受監理規範...之金融機構'), default=False
    )
    # g.是否為我國政府機關主管之基金。
    is_gov_fund = models.BooleanField(_('是否為我國政府機關主管之基金'), default=False)
    # h.是否為員工持股信託、員工福利儲蓄信託
    is_employee_trust = models.BooleanField(_('是否為員工持股信託、員工福利儲蓄信託'), default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    approval_requests = GenericRelation(ApprovalRequest, related_query_name='client_assessment')

    class Meta:
        verbose_name = _('客戶評估表')
        verbose_name_plural = _('客戶評估表')
        ordering = ['-created_at']

    def __str__(self):
        return self.company_name

    def get_absolute_url(self):
        return reverse('registration:client_assessment_update', kwargs={'pk': self.pk})

    def get_approval_request(self):
        """取得最新的核准請求"""
        from modules.workflow.services import get_approval_request
        return get_approval_request(self)

    def can_submit_for_approval(self):
        """檢查是否可以送出核准"""
        request = self.get_approval_request()
        return not request or request.status in ['DRAFT', 'RETURNED']

    def can_user_approve(self, user):
        """檢查使用者是否可以核准"""
        from modules.workflow.services import get_effective_approver
        
        request = self.get_approval_request()
        if not request or request.status != 'PENDING':
            return False
            
        if not request.current_step:
            return False
            
        # 取得指定的核准者
        step_approver = request.current_step.get_approver(self)
        
        if not step_approver:
            return False
            
        # 檢查是否為指定核准者（考慮代理人）
        from django.contrib.auth.models import Group
        if isinstance(step_approver, Group):
            # 檢查使用者是否屬於該群組
            if user.groups.filter(id=step_approver.id).exists():
                return True
            # 檢查是否有人代理該群組成員
            effective_approver, _ = get_effective_approver(user, request)
            return effective_approver != user
        else:
            # 檢查是否為指定使用者或代理人
            effective_approver, original = get_effective_approver(step_approver, request)
            return effective_approver == user

    def can_user_cancel(self, user):
        """檢查使用者是否可以撤回"""
        request = self.get_approval_request()
        if not request or request.status not in ['PENDING', 'RETURNED']:
            return False
        return request.requester == user
