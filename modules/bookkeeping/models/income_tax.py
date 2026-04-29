import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import BaseModel
from .bookkeeping_client import BookkeepingClient


# ============================================================
# 文件上傳路徑
# ============================================================
def get_income_tax_document_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    tax_id = instance.year_record.client.tax_id or 'unknown_client'
    year = instance.year_record.year
    item_type = instance.__class__.__name__.lower()
    return f'income_tax/documents/{tax_id}/{year}/{item_type}/{new_filename}'


# ============================================================
# 共用 Choices（可跨 Model 使用）
# ============================================================
class FilingStatus(models.TextChoices):
    NOT_NOTIFIED = 'not_notified', '尚未通知'
    WAITING = 'waiting', '等待回覆'
    PAID = 'paid', '繳納完成'
    NO_PAYMENT_NEEDED = 'no_payment_needed', '無須繳納'


class PaymentMethod(models.TextChoices):
    SELF_PAY = 'self_pay', '自行繳納'
    OFFICE_PAY = 'office_pay', '事務所代繳'
    AUTO_DEBIT = 'auto_debit', '自動扣款'
    NO_PAYMENT = 'no_payment', '不用繳稅'


class NotificationMethod(models.TextChoices):
    LINE = 'line', 'Line'
    EMAIL = 'email', 'Email'
    BOTH = 'both', 'Line + Email'


class FilingMethod(models.TextChoices):
    BOOK_REVIEW = 'book_review', '書審'
    STANDARD = 'standard', '所標'
    INDUSTRY_PROFIT = 'industry_profit', '同業利潤'
    CPA_CERTIFIED = 'cpa_certified', '簽證'
    AUDIT = 'audit', '查帳'


# ============================================================
# 第 1 層：靜態設定
# ============================================================
class IncomeTaxSetting(BaseModel):
    """所得稅申報設定 — 第一層（靜態設定表）"""
    client = models.OneToOneField(
        BookkeepingClient,
        on_delete=models.CASCADE,
        related_name='income_tax_setting',
        verbose_name=_('客戶'),
    )
    filing_method = models.CharField(
        _('申報方式'), max_length=20,
        choices=FilingMethod.choices,
        default=FilingMethod.BOOK_REVIEW,
    )
    notification_method = models.CharField(
        _('通知方式'), max_length=10,
        choices=NotificationMethod.choices,
        blank=True, null=True,
    )
    payment_method = models.CharField(
        _('預設繳稅方式'), max_length=20,
        choices=PaymentMethod.choices,
        blank=True, null=True,
    )

    class Meta:
        verbose_name = _('所得稅申報設定')
        verbose_name_plural = _('所得稅申報設定')

    def __str__(self):
        return f"{self.client.name} - 所得稅設定"


# ============================================================
# 第 2 層：年度籃子
# ============================================================
class IncomeTaxYear(BaseModel):
    """所得稅申報年度 — 第二層（年度籃子）"""
    client = models.ForeignKey(
        BookkeepingClient,
        on_delete=models.CASCADE,
        related_name='income_tax_years',
        verbose_name=_('客戶'),
    )
    year = models.PositiveIntegerField(_('年度(民國)'))

    class Meta:
        verbose_name = _('所得稅年度')
        verbose_name_plural = _('所得稅年度')
        unique_together = ('client', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"{self.client.name} - {self.year}年度 (所得稅)"


# ============================================================
# 抽象基底：所有所得稅項目共用的欄位
# ============================================================
class IncomeTaxItemBase(BaseModel):
    """
    所得稅項目抽象基底 — 不建資料表。
    ProvisionalTax / WithholdingTax / DividendTax / IncomeTaxFiling 繼承此類。
    """
    filing_status = models.CharField(
        _('繳納狀態'), max_length=20,
        choices=FilingStatus.choices,
        default=FilingStatus.NOT_NOTIFIED,
    )
    filing_date = models.DateField(_('申報日期'), null=True, blank=True)
    tax_deadline = models.DateField(_('繳稅截止日'), null=True, blank=True)
    payable_tax = models.DecimalField(
        _('應納稅額'), max_digits=15, decimal_places=0, default=0,
    )
    payment_method = models.CharField(
        _('繳稅方式'), max_length=20,
        choices=PaymentMethod.choices,
        blank=True, null=True,
    )
    is_filed = models.BooleanField(_('是否已申報'), default=False)
    filing_document = models.FileField(
        _('申報書'), upload_to=get_income_tax_document_path,
        blank=True, null=True,
    )
    confirm_token = models.UUIDField(
        _('確認Token'), default=uuid.uuid4, unique=True, editable=False,
    )
    notes = models.TextField(_('備註'), blank=True)

    class Meta:
        abstract = True

    # ── 通知系統代理 property ──
    @property
    def email(self):
        return getattr(self.year_record.client, 'email', None)

    @property
    def line_id(self):
        return getattr(self.year_record.client, 'line_id', None)

    @property
    def room_id(self):
        return getattr(self.year_record.client, 'room_id', None)


# ============================================================
# 暫繳申報免繳 Checklist 預設值
# ============================================================
DEFAULT_PROVISIONAL_CHECKLIST = [
    {'key': 'sole_partnership', 'label': '獨資、合夥組織之營利事業及經核定之小規模營利事業。', 'checked': False},
    {'key': 'tax_exempt_org', 'label': '合於免稅規定之教育、文化、公益、慈善機關或團體及其附屬作業組織、不對外營業之消費合作社、公有事業。', 'checked': False},
    {'key': 'new_business', 'label': '本年度新開業者。', 'checked': False},
    {'key': 'dissolution', 'label': '營利事業於暫繳申報期間屆滿前遇有解散、廢止、合併或轉讓情事，其依所得稅法75條規定應辦理當期決算申報者。', 'checked': False},
    {'key': 'zero_invoice', 'label': '上半年發票金額為0。', 'checked': False},
]


# ============================================================
# 第 3 層 ① — 暫繳申報（9 月）
# ============================================================
class ProvisionalTax(IncomeTaxItemBase):
    """暫繳申報"""
    year_record = models.OneToOneField(
        IncomeTaxYear,
        on_delete=models.CASCADE,
        related_name='provisional_tax',
        verbose_name=_('所屬年度'),
    )
    last_year_tax = models.DecimalField(
        _('去年應納稅額'), max_digits=15, decimal_places=0, default=0,
    )
    provisional_amount = models.DecimalField(
        _('本年暫繳金額'), max_digits=15, decimal_places=0, default=0,
    )
    provisional_deadline = models.DateField(
        _('暫繳截止日'), null=True, blank=True,
    )
    checklist = models.JSONField(
        _('免繳檢查表'),
        default=list,
        blank=True,
        help_text=_('暫繳免繳的檢查項目'),
    )

    class Meta:
        verbose_name = _('暫繳申報')
        verbose_name_plural = _('暫繳申報')

    def __str__(self):
        return f"{self.year_record} - 暫繳"

    def save(self, *args, **kwargs):
        if not self.checklist:
            import copy
            self.checklist = copy.deepcopy(DEFAULT_PROVISIONAL_CHECKLIST)
        super().save(*args, **kwargs)


# ============================================================
# 第 3 層 ② — 扣繳申報（次年 1 月）
# ============================================================
class WithholdingTax(IncomeTaxItemBase):
    """扣繳申報"""
    class SalaryPaymentMethod(models.TextChoices):
        BEGINNING = 'beginning', '月初'
        END = 'end', '月底'

    year_record = models.OneToOneField(
        IncomeTaxYear,
        on_delete=models.CASCADE,
        related_name='withholding_tax',
        verbose_name=_('所屬年度'),
    )
    salary_payment_method = models.CharField(
        _('薪資發放方式'), max_length=20,
        choices=SalaryPaymentMethod.choices,
        blank=True, null=True,
    )
    interest_income = models.DecimalField(
        _('利息收入'), max_digits=15, decimal_places=0, default=0,
    )

    class Meta:
        verbose_name = _('扣繳申報')
        verbose_name_plural = _('扣繳申報')

    def __str__(self):
        return f"{self.year_record} - 扣繳"


class WithholdingDetail(BaseModel):
    """扣繳各類所得明細（inline 表格）— 每筆代表一個受領人"""
    class IncomeCategory(models.TextChoices):
        SALARY = 'salary', '薪資所得'
        PROFESSIONAL = 'professional', '執行業務所得'
        RENTAL = 'rental', '租金所得'
        INTEREST = 'interest', '利息所得'
        OTHER = 'other', '其他所得'

    withholding_tax = models.ForeignKey(
        WithholdingTax,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name=_('所屬扣繳申報'),
    )
    certificate_no = models.CharField(
        _('證號'), max_length=50, blank=True,
    )
    recipient_name = models.CharField(
        _('姓名'), max_length=100, blank=True,
    )
    id_number = models.CharField(
        _('身分證字號'), max_length=20, blank=True,
    )
    address = models.CharField(
        _('地址'), max_length=255, blank=True,
    )
    income_category = models.CharField(
        _('所得類別'), max_length=20,
        choices=IncomeCategory.choices,
        default=IncomeCategory.SALARY,
    )
    category_name = models.CharField(
        _('類別名稱'), max_length=100, blank=True,
    )
    lease_no = models.CharField(
        _('租賃編號'), max_length=50, blank=True,
    )
    total_amount = models.DecimalField(
        _('申報總額'), max_digits=15, decimal_places=0, default=0,
    )
    tax_withheld = models.DecimalField(
        _('扣繳稅額'), max_digits=15, decimal_places=0, default=0,
    )
    supplementary_premium = models.DecimalField(
        _('補充保費'), max_digits=15, decimal_places=0, default=0,
    )
    recipient_count = models.PositiveIntegerField(
        _('所得人數'), default=0,
    )
    detail_notes = models.TextField(_('備註'), blank=True)

    class Meta:
        verbose_name = _('扣繳所得明細')
        verbose_name_plural = _('扣繳所得明細')
        ordering = ['income_category']

    def __str__(self):
        return f"{self.withholding_tax} - {self.recipient_name or self.get_income_category_display()}"


class WithholdingMonthlyBreakdown(BaseModel):
    """扣繳月分明細 — Modal 表格每一列"""
    class Period(models.TextChoices):
        PREV_BONUS = 'prev_bonus', '前期年終'
        PREV_SALARY = 'prev_salary', '前期薪資'
        M01 = 'm01', '1月'
        M02 = 'm02', '2月'
        M03 = 'm03', '3月'
        M04 = 'm04', '4月'
        M05 = 'm05', '5月'
        M06 = 'm06', '6月'
        M07 = 'm07', '7月'
        M08 = 'm08', '8月'
        M09 = 'm09', '9月'
        M10 = 'm10', '10月'
        M11 = 'm11', '11月'
        M12 = 'm12', '12月'
        CUR_BONUS = 'cur_bonus', '當期年終'
        DRAGON_BOAT = 'dragon_boat', '端午獎金'
        MID_AUTUMN = 'mid_autumn', '中秋獎金'

    detail = models.ForeignKey(
        WithholdingDetail,
        on_delete=models.CASCADE,
        related_name='monthly_breakdowns',
        verbose_name=_('所屬扣繳明細'),
    )
    period = models.CharField(
        _('期間'), max_length=20,
        choices=Period.choices,
    )
    salary = models.DecimalField(
        _('薪資'), max_digits=15, decimal_places=0, default=0,
    )
    retirement_contribution = models.DecimalField(
        _('退休金自提'), max_digits=15, decimal_places=0, default=0,
    )
    tax = models.DecimalField(
        _('稅額'), max_digits=15, decimal_places=0, default=0,
    )
    meal_allowance = models.DecimalField(
        _('伙食費'), max_digits=15, decimal_places=0, default=0,
    )
    overtime_pay = models.DecimalField(
        _('加班費'), max_digits=15, decimal_places=0, default=0,
    )

    class Meta:
        verbose_name = _('扣繳月分明細')
        verbose_name_plural = _('扣繳月分明細')
        ordering = ['period']
        unique_together = [('detail', 'period')]

    def __str__(self):
        return f"{self.detail} - {self.get_period_display()}"


# ============================================================
# 第 3 層 ③ — 股利申報（次年 1 月）
# ============================================================
class DividendTax(IncomeTaxItemBase):
    """股利申報"""
    year_record = models.OneToOneField(
        IncomeTaxYear,
        on_delete=models.CASCADE,
        related_name='dividend_tax',
        verbose_name=_('所屬年度'),
    )
    last_year_profit = models.DecimalField(
        _('去年淨利'), max_digits=15, decimal_places=0, default=0,
    )
    accumulated_loss = models.DecimalField(
        _('累積虧損'), max_digits=15, decimal_places=0, default=0,
    )
    distributable_amount = models.DecimalField(
        _('彌補虧損後可供分配'), max_digits=15, decimal_places=0, default=0,
    )
    distributed_amount = models.DecimalField(
        _('分配金額'), max_digits=15, decimal_places=0, default=0,
    )
    undistributed_surtax = models.DecimalField(
        _('未分配盈餘加徵稅額'), max_digits=15, decimal_places=0, default=0,
    )

    # ── 外部確認 ──
    class ConfirmationStatus(models.TextChoices):
        PENDING = 'pending', _('待確認')
        CONFIRMED = 'confirmed', _('已確認')
        DISPUTED = 'disputed', _('有異議')

    confirmation_status = models.CharField(
        _('確認狀態'), max_length=20,
        choices=ConfirmationStatus.choices,
        default=ConfirmationStatus.PENDING,
    )
    confirmed_at = models.DateTimeField(_('確認時間'), null=True, blank=True)
    client_feedback = models.TextField(_('客戶回覆'), blank=True)

    # ── 股東名冊匯入基準日 ──
    import_date = models.DateField(_('匯入基準日'), null=True, blank=True)

    class Meta:
        verbose_name = _('股利申報')
        verbose_name_plural = _('股利申報')

    def __str__(self):
        return f"{self.year_record} - 股利"


class ShareholderDividend(BaseModel):
    """股東名冊（inline 表格）"""
    dividend_tax = models.ForeignKey(
        DividendTax,
        on_delete=models.CASCADE,
        related_name='shareholders',
        verbose_name=_('所屬股利申報'),
    )
    shareholder_name = models.CharField(_('股東姓名'), max_length=100)
    id_number = models.CharField(_('身分證/統編'), max_length=20, blank=True)
    stock_type = models.CharField(
        _('股票種類'), max_length=20, blank=True, default='COMMON',
    )
    share_count = models.IntegerField(_('股數'), default=0)
    face_value = models.DecimalField(
        _('面額'), max_digits=10, decimal_places=0, default=10,
    )
    share_amount = models.DecimalField(
        _('金額'), max_digits=15, decimal_places=0, default=0,
    )
    share_ratio = models.DecimalField(
        _('持股比例 (%)'), max_digits=6, decimal_places=2, default=0,
    )
    dividend_amount = models.DecimalField(
        _('分配金額'), max_digits=15, decimal_places=0, default=0,
    )
    personal_tax_rate = models.DecimalField(
        _('個人稅率 (%)'), max_digits=5, decimal_places=2, default=0,
    )
    tax_amount = models.DecimalField(
        _('個人所得稅'), max_digits=15, decimal_places=0, default=0,
    )
    imputation_credit = models.DecimalField(
        _('股東可扣抵稅額'), max_digits=15, decimal_places=0, default=0,
    )
    insurance_base = models.DecimalField(
        _('負責人身分投保金額'), max_digits=15, decimal_places=0, default=0,
    )
    supplement_premium_rate = models.DecimalField(
        _('補充保費稅率 (%)'), max_digits=5, decimal_places=2, default=2.11,
    )
    supplement_premium = models.DecimalField(
        _('補充保費'), max_digits=15, decimal_places=0, default=0,
    )
    total_tax_premium = models.DecimalField(
        _('個人稅+補充保費'), max_digits=15, decimal_places=0, default=0,
    )

    class Meta:
        verbose_name = _('股東股利明細')
        verbose_name_plural = _('股東股利明細')
        ordering = ['-share_ratio']

    def __str__(self):
        return f"{self.dividend_tax} - {self.shareholder_name}"


# ============================================================
# 第 3 層 ④ — 所得稅申報（次年 5 月）
# ============================================================
# 預設檢查表項目
DEFAULT_INCOME_TAX_CHECKLIST = [
    {'key': 'revenue_401', 'label': '收入與401調節表相符', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'income_tax_expense', 'label': '所得稅費用相符', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'entertainment_limit', 'label': '交際費未超限', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'bad_debt_limit', 'label': '壞帳費用未超限', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'welfare_limit', 'label': '職工福利未超限', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'provisional_withholding', 'label': '暫繳及扣繳要扣除', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'undistributed_surtax', 'label': '未分配加徵稅額相符', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'undistributed_99', 'label': '99未分配盈餘加徵', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'cost_schedule', 'label': '成本表相符', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'withholding_reconciliation', 'label': '扣繳調節表已完成', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'land_c4', 'label': '土地交易填C4表', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'nta_adjustment', 'label': '國稅局調整已入帳', 'filing_amount': '', 'status': '', 'note': ''},
    {'key': 'client_instructions', 'label': '客戶交代事項已完成', 'filing_amount': '', 'status': '', 'note': ''},
]


class IncomeTaxFiling(IncomeTaxItemBase):
    """公司所得稅申報"""
    year_record = models.OneToOneField(
        IncomeTaxYear,
        on_delete=models.CASCADE,
        related_name='income_tax_filing',
        verbose_name=_('所屬年度'),
    )
    taxable_income = models.DecimalField(
        _('本年度課稅所得'), max_digits=15, decimal_places=0, default=0,
    )
    annual_tax = models.DecimalField(
        _('本年度應納稅額'), max_digits=15, decimal_places=0, default=0,
    )
    provisional_credit = models.DecimalField(
        _('暫繳金額'), max_digits=15, decimal_places=0, default=0,
        help_text=_('可由暫繳申報帶入'),
    )
    withholding_credit = models.DecimalField(
        _('扣繳金額'), max_digits=15, decimal_places=0, default=0,
    )
    self_pay_amount = models.DecimalField(
        _('本年度應自行補繳稅額'), max_digits=15, decimal_places=0, default=0,
    )
    undistributed_earnings = models.DecimalField(
        _('未分配盈餘金額'), max_digits=15, decimal_places=0, default=0,
        help_text=_('可由股利申報帶入'),
    )
    undistributed_surtax = models.DecimalField(
        _('未分配盈餘加徵稅額'), max_digits=15, decimal_places=0, default=0,
    )
    total_payable = models.DecimalField(
        _('本稅+未分配加徵合計'), max_digits=15, decimal_places=0, default=0,
    )
    checklist = models.JSONField(
        _('稅法檢查表'),
        default=list,
        blank=True,
        help_text=_('JSON 結構，存放各檢查項目及備註'),
    )
    media_file = models.FileField(
        _('媒體檔'), upload_to='income_tax/media/',
        blank=True, null=True,
    )
    tax_bill_document = models.FileField(
        _('繳款書'), upload_to=get_income_tax_document_path,
        blank=True, null=True,
    )
    reconciliation = models.JSONField(
        _('扣繳調節表'),
        default=list,
        blank=True,
        help_text=_('JSON list，存放扣繳調節表各列資料'),
    )

    class Meta:
        verbose_name = _('所得稅申報')
        verbose_name_plural = _('所得稅申報')

    def __str__(self):
        return f"{self.year_record} - 所得稅申報"

    def save(self, *args, **kwargs):
        # 初次建立時填入預設檢查表
        if not self.checklist:
            import copy
            self.checklist = copy.deepcopy(DEFAULT_INCOME_TAX_CHECKLIST)
        super().save(*args, **kwargs)

    # ── 自動帶入 property ──
    @property
    def provisional_amount_from_sibling(self):
        """從同年度暫繳帶入暫繳金額（參考用，不自動覆蓋欄位）"""
        try:
            return self.year_record.provisional_tax.provisional_amount
        except ProvisionalTax.DoesNotExist:
            return 0

    @property
    def dividend_surtax_from_sibling(self):
        """從同年度股利帶入未分配盈餘加徵（參考用）"""
        try:
            return self.year_record.dividend_tax.undistributed_surtax
        except DividendTax.DoesNotExist:
            return 0


# ============================================================
# Signals — 自動建立
# ============================================================
@receiver(post_save, sender=BookkeepingClient)
def auto_create_income_tax_setting(sender, instance, created, **kwargs):
    """新增 BookkeepingClient 時，自動建立 IncomeTaxSetting"""
    if created:
        IncomeTaxSetting.objects.get_or_create(client=instance)


@receiver(post_save, sender=IncomeTaxYear)
def auto_create_income_tax_items(sender, instance, created, **kwargs):
    """新增 IncomeTaxYear 時，自動建立 5 個子項目"""
    if created:
        ProvisionalTax.objects.get_or_create(year_record=instance)
        WithholdingTax.objects.get_or_create(year_record=instance)
        DividendTax.objects.get_or_create(year_record=instance)
        IncomeTaxFiling.objects.get_or_create(year_record=instance)
        # 媒體檔解析資料（延遲匯入，避免循環引用）
        from .income_tax_media import IncomeTaxMediaData
        IncomeTaxMediaData.objects.get_or_create(year_record=instance)
