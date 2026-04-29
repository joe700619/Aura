import os
import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .bookkeeping_client import BookkeepingClient


# ============================================================
# 檔案上傳路徑
# ============================================================
def _build_path(folder, instance, filename):
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    client_id = getattr(instance, 'client_id', None) or 'unknown'
    return f'service_remuneration/{folder}/{client_id}/{new_filename}'


def signature_upload_path(instance, filename):
    # Kept for backward compatibility with migration 0042; field removed in 0043.
    return _build_path('signatures', instance, filename)


def id_front_upload_path(instance, filename):
    return _build_path('id_front', instance, filename)


def id_back_upload_path(instance, filename):
    return _build_path('id_back', instance, filename)


def withholding_slip_upload_path(instance, filename):
    return _build_path('withholding_slips', instance, filename)


def supp_premium_slip_upload_path(instance, filename):
    return _build_path('supp_premium_slips', instance, filename)


# ============================================================
# 稅率設定
# ============================================================
class ServiceRemunerationTaxRate(BaseModel):
    """勞務報酬稅率設定 — 一列一筆規則。

    code 命名規則：
    - 9B / 9A / 50 / 92 ：本國人申報類別
    - 9A-98 / 9A-99 ：執行業務細分（含費用率）
    - FOREIGN_LT_183 / FOREIGN_GTE_183 ：外國人在臺
    """
    code = models.CharField(_('代碼'), max_length=30, unique=True)
    label = models.CharField(_('名稱'), max_length=100)
    withholding_rate = models.DecimalField(
        _('扣繳率 (%)'), max_digits=5, decimal_places=2, default=Decimal('0'),
    )
    expense_rate = models.DecimalField(
        _('費用率 (%)'), max_digits=5, decimal_places=2,
        default=Decimal('0'),
        help_text=_('僅執行業務類別需填寫；其他類別填 0。'),
    )
    description = models.CharField(_('說明'), max_length=255, blank=True)
    is_active = models.BooleanField(_('啟用'), default=True)
    sort_order = models.PositiveIntegerField(_('排序'), default=0)

    class Meta:
        verbose_name = _('勞務報酬稅率設定')
        verbose_name_plural = _('勞務報酬稅率設定')
        ordering = ['sort_order', 'code']

    def __str__(self):
        return f"{self.code} - {self.label} ({self.withholding_rate}%)"


class NHIConfig(BaseModel):
    """二代健保補充保費設定（singleton — 僅取第一筆）"""
    threshold = models.DecimalField(
        _('起徵額'), max_digits=12, decimal_places=0,
        default=Decimal('20000'),
        help_text=_('單筆金額超過此值才需扣補充保費'),
    )
    rate = models.DecimalField(
        _('補充保費率 (%)'), max_digits=5, decimal_places=2,
        default=Decimal('2.11'),
    )

    class Meta:
        verbose_name = _('二代健保設定')
        verbose_name_plural = _('二代健保設定')

    def __str__(self):
        return f"二代健保 {self.rate}% (起徵額 {self.threshold})"

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create()
        return obj


# ============================================================
# 主表
# ============================================================
class ServiceRemuneration(BaseModel):
    """勞務報酬單"""

    class Nationality(models.TextChoices):
        LOCAL = 'local', _('本國人')
        FOREIGN_LT_183 = 'foreign_lt_183', _('外國人在臺未滿183天')
        FOREIGN_GTE_183 = 'foreign_gte_183', _('外國人在臺滿183天')

    class IncomeCategory(models.TextChoices):
        C9B = '9B', _('9B 稿費')
        C9A = '9A', _('9A 執行業務所得')
        C50 = '50', _('50 薪資所得')
        C92 = '92', _('92 其他所得')
        RENT = '51', _('租金')

    class ProfessionalCategory(models.TextChoices):
        C98 = '98', _('[98] 非自行出版稿費等(費用率30%)')
        C99 = '99', _('[99] 自行出版稿費等(費用率75%)')

    class PaymentMethod(models.TextChoices):
        TRANSFER = 'transfer', _('匯款')
        CASH = 'cash', _('現金')
        CHECK = 'check', _('支票')
        VOUCHER = 'voucher', _('禮券')

    class ConfirmationStatus(models.TextChoices):
        PENDING = 'pending', _('待確認')
        CONFIRMED = 'confirmed', _('已確認')

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', _('待繳納')
        PAID = 'paid', _('已繳納')

    # ── 關聯 ──
    client = models.ForeignKey(
        BookkeepingClient, on_delete=models.CASCADE,
        related_name='service_remunerations',
        verbose_name=_('客戶'),
    )
    confirm_token = models.UUIDField(
        _('確認Token'), default=uuid.uuid4, unique=True, editable=False,
    )

    # ── 所得人基本資料 ──
    recipient_name = models.CharField(_('姓名'), max_length=100)
    recipient_email = models.EmailField(_('Email'), blank=True)
    nationality = models.CharField(
        _('國籍'), max_length=20,
        choices=Nationality.choices, default=Nationality.LOCAL,
    )
    id_number = models.CharField(_('身分證字號'), max_length=20, blank=True)
    has_nhi = models.BooleanField(_('是否投保健保'), default=False)
    residence_address = models.CharField(_('戶籍地址'), max_length=255, blank=True)
    phone = models.CharField(_('聯絡電話'), max_length=30, blank=True)
    joined_union = models.BooleanField(_('已加入工會'), default=False)

    # ── 勞報資料 ──
    income_category = models.CharField(
        _('申報類別'), max_length=10,
        choices=IncomeCategory.choices, default=IncomeCategory.C9A,
    )
    professional_category = models.CharField(
        _('執行業務類別'), max_length=10,
        choices=ProfessionalCategory.choices, blank=True,
    )
    amount = models.DecimalField(_('金額'), max_digits=15, decimal_places=0, default=0)
    service_content = models.TextField(_('勞務內容'), blank=True)
    service_start_date = models.DateField(_('勞務開始日期'), null=True, blank=True)
    service_end_date = models.DateField(_('勞務結束日期'), null=True, blank=True)
    filing_date = models.DateField(_('填表日期'), null=True, blank=True)
    company_name = models.CharField(_('公司名稱'), max_length=200, blank=True)

    # ── 試算（存檔時計算寫入快照）──
    withholding_tax = models.DecimalField(
        _('代扣所得稅'), max_digits=15, decimal_places=0, default=0,
    )
    supplementary_premium = models.DecimalField(
        _('二代健保補充保費'), max_digits=15, decimal_places=0, default=0,
    )
    actual_payment = models.DecimalField(
        _('實際支付金額'), max_digits=15, decimal_places=0, default=0,
    )

    # ── 支付資料 ──
    payment_method = models.CharField(
        _('付款方式'), max_length=20,
        choices=PaymentMethod.choices, blank=True,
    )
    bank_code = models.CharField(_('所得人銀行'), max_length=20, blank=True)
    branch_name = models.CharField(_('銀行分行'), max_length=100, blank=True)
    bank_account = models.CharField(_('所得人帳號'), max_length=50, blank=True)
    account_holder = models.CharField(_('所得人戶名'), max_length=100, blank=True)

    # ── 附件圖片 ──
    id_front_image = models.ImageField(
        _('身分證正面'), upload_to=id_front_upload_path,
        blank=True, null=True,
    )
    id_back_image = models.ImageField(
        _('身分證反面'), upload_to=id_back_upload_path,
        blank=True, null=True,
    )

    # ── 狀態 ──
    confirmation_status = models.CharField(
        _('確認狀態'), max_length=20,
        choices=ConfirmationStatus.choices,
        default=ConfirmationStatus.PENDING,
    )
    confirmed_at = models.DateTimeField(_('確認時間'), null=True, blank=True)
    skip_email_confirm = models.BooleanField(_('跳過Email確認'), default=False)
    email_sent_at = models.DateTimeField(_('Email寄送時間'), null=True, blank=True)

    payment_status = models.CharField(
        _('繳納狀態'), max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )

    # ── 繳款憑證 ──
    withholding_payment_slip = models.FileField(
        _('扣繳繳款單'), upload_to=withholding_slip_upload_path,
        blank=True, null=True,
    )
    supplementary_payment_slip = models.FileField(
        _('補充保費繳款單'), upload_to=supp_premium_slip_upload_path,
        blank=True, null=True,
    )

    class Meta:
        verbose_name = _('勞務報酬單')
        verbose_name_plural = _('勞務報酬單')
        ordering = ['-filing_date', '-created_at']

    def __str__(self):
        return f"{self.recipient_name} - {self.amount} ({self.get_income_category_display()})"

    # ── 計算邏輯 ──
    def _resolve_tax_rate_code(self):
        """依國籍+類別決定要查哪一筆稅率。"""
        if self.nationality == self.Nationality.FOREIGN_LT_183:
            return 'FOREIGN_LT_183'
        if self.nationality == self.Nationality.FOREIGN_GTE_183:
            return 'FOREIGN_GTE_183'
        # 本國人
        if self.income_category == self.IncomeCategory.C9A and self.professional_category:
            return f'9A-{self.professional_category}'
        return self.income_category

    def calculate(self):
        """依規則重算 withholding_tax / supplementary_premium / actual_payment。"""
        amount = Decimal(self.amount or 0)
        cat = self.income_category

        # 扣繳稅額
        if cat == self.IncomeCategory.C50:
            wh_tax = (amount * Decimal('0.05')).quantize(Decimal('1')) if amount >= 90501 else Decimal('0')
        elif cat == self.IncomeCategory.C92:
            wh_tax = Decimal('0')
        else:
            tentative = (amount * Decimal('0.1')).quantize(Decimal('1'))
            wh_tax = tentative if tentative > 2000 else Decimal('0')

        # 補充保費（已加入工會免扣）
        nhi = NHIConfig.get_solo()
        nhi_rate = nhi.rate / Decimal('100')
        supp = Decimal('0')
        if not self.joined_union:
            if cat == self.IncomeCategory.C50:
                if amount > 29500:
                    supp = (amount * nhi_rate).quantize(Decimal('1'))
            elif cat != self.IncomeCategory.C92:
                if amount >= 20000:
                    base = min(amount, Decimal('10000000'))
                    supp = (base * nhi_rate).quantize(Decimal('1'))

        self.withholding_tax = wh_tax
        self.supplementary_premium = supp
        self.actual_payment = amount - wh_tax - supp

    def save(self, *args, **kwargs):
        self.calculate()
        super().save(*args, **kwargs)
