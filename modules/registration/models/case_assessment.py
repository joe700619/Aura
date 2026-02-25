from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .client_assessment import ClientAssessment

class CaseAssessment(models.Model):
    class RiskLevel(models.IntegerChoices):
        NORMAL = 0, _('一般風險')
        HIGH = 1, _('高風險')

    client_assessment = models.ForeignKey(
        ClientAssessment,
        on_delete=models.CASCADE,
        related_name='case_assessments',
        verbose_name=_('客戶評估表'),
        blank=True, null=True
    )
    
    # Basic Data
    company_name = models.CharField(_('公司名稱'), max_length=255, blank=True, null=True)
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True, null=True)
    line_id = models.CharField(_('Line ID'), max_length=100, blank=True, null=True)
    room_id = models.CharField(_('Room ID'), max_length=100, blank=True, null=True)

    # Contact Data
    main_contact = models.CharField(_('主要聯絡人'), max_length=100, blank=True, null=True)
    mobile = models.CharField(_('手機'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('電話'), max_length=50, blank=True, null=True)
    address = models.CharField(_('通訊地址'), max_length=255, blank=True, null=True)

    date = models.DateField(_('評估日期'), default=timezone.now)
    registration_no = models.CharField(_('登記案件編號'), max_length=50, blank=True, null=True)
    risk_level = models.IntegerField(_('風險層級'), choices=RiskLevel.choices, default=RiskLevel.NORMAL)
    
    # Status
    is_accepted = models.BooleanField(_('案件承接與否'), default=True)
    is_completed = models.BooleanField(_('案件完成否'), default=False)
    needs_reporting = models.BooleanField(_('案件是否符合通報義務'), default=False)

    # Transaction Types
    transaction_50 = models.BooleanField(_('50 買賣不動產'), default=False)
    transaction_51 = models.BooleanField(_('51 管理客戶金錢、證券或其他資產'), default=False)
    transaction_52 = models.BooleanField(_('52 管理銀行、儲蓄或證券帳戶'), default=False)
    transaction_53 = models.BooleanField(_('53 有關提供公司設立、營運或管理之資金籌劃'), default=True)
    transaction_54 = models.BooleanField(_('54 法人或法律協議之設立、營運或管理以及買賣事業體'), default=False)
    transaction_55 = models.BooleanField(_('55 關於法人之籌備或設立事項'), default=False)
    transaction_56 = models.BooleanField(_('56 擔任或安排他人擔任公司董事或秘書、合夥之合夥人或在其他法人組織之類似職位'), default=False)
    transaction_57 = models.BooleanField(_('57 提供公司、合夥、信託、其他法人或協議註冊之辦公室、營業地址、居住所、通訊或管理地址'), default=False)
    transaction_58 = models.BooleanField(_('58 擔任或安排他人擔任信託或其他類似契約性質之受託人或其他相同角色'), default=False)
    transaction_59 = models.BooleanField(_('59 擔任或安排他人擔任實質持股股東'), default=False)

    # Warning Transactions
    warning_1 = models.BooleanField(_('1. 酬金或交易金額高於新臺幣50萬元，客戶無正當理由，自行或要求多次或連續以略低於新臺幣50萬之現金支付。'), default=False)
    warning_2 = models.BooleanField(_('2. 酬金或交易金額高於新臺幣50萬元，客戶無正當理由，以現金、外幣現金、旅行支票、外幣匯票或其他無記名金融工具支付。'), default=False)
    warning_3 = models.BooleanField(_('3. 無正當理由要求立即買賣不動產或事業體。'), default=False)
    warning_4 = models.BooleanField(_('4. 客戶為法務部依資恐防制法公告制裁之個人、法人或團體，或法務部公布之其他國家、國際組織認定或追查之恐怖組織、恐怖分子。'), default=False)
    warning_5 = models.BooleanField(_('5. 交易疑似與恐怖活動、恐怖組織、資助恐怖主義或武器擴散有關聯。'), default=False)
    warning_6 = models.BooleanField(_('6. 為客戶準備或進行洗錢防制法第五條第三項第五款受指定各項交易，客戶未能說明具體事由，或其事由顯不屬實。'), default=False)
    warning_7 = models.BooleanField(_('7. 委任關係結束後，發現客戶否認該委任、無該客戶存在或其他有事實足認該客戶係被他人所冒用。'), default=False)
    warning_8 = models.BooleanField(_('8. 其他疑似洗錢或資恐交易情事。'), default=False)

    # Appendix
    appendix_1 = models.BooleanField(_('1. 法務部調查局之網頁：http://www.mjib.gov.tw/MLPC，確認其國籍是否為制裁名單中之國家。'), default=False)
    appendix_1_note = models.CharField(_('備註'), max_length=255, blank=True, null=True)
    
    appendix_2 = models.BooleanField(_('2. 台灣集中保管結算所：http://aml.tdcc.com.tw/AMLP，以帳號登入後，確認該人物是否為 PEP。'), default=False)
    appendix_2_note = models.CharField(_('備註'), max_length=255, blank=True, null=True)
    
    appendix_3 = models.BooleanField(_('3. 取得資本簽證必要文件'), default=True)
    appendix_3_note = models.CharField(_('備註'), max_length=255, blank=True, null=True)
    
    appendix_4 = models.BooleanField(_('4. 取得資金來源證明'), default=True)
    appendix_4_note = models.CharField(_('備註'), max_length=255, blank=True, null=True)

    note = models.TextField(_('說明'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('案件評估表')
        verbose_name_plural = _('案件評估表')
        ordering = ['-date']

    def __str__(self):
        return f"{self.registration_no} ({self.date})" if self.registration_no else f"案件評估 ({self.date})"

    def save(self, *args, **kwargs):
        # Snapshot data from ClientAssessment if linked and fields are empty
        if self.client_assessment:
            if not self.company_name:
                self.company_name = self.client_assessment.company_name
            if not self.unified_business_no:
                self.unified_business_no = self.client_assessment.unified_business_no
            if not self.line_id:
                self.line_id = self.client_assessment.line_id
            if not self.room_id:
                self.room_id = self.client_assessment.room_id
            
            if not self.main_contact:
                self.main_contact = self.client_assessment.main_contact
            if not self.mobile:
                self.mobile = self.client_assessment.mobile
            if not self.phone:
                self.phone = self.client_assessment.phone
            if not self.address:
                self.address = self.client_assessment.address
        super().save(*args, **kwargs)

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
        return reverse('registration:case_assessment_update', kwargs={'pk': self.pk})
