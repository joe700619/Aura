import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from .income_tax import IncomeTaxYear


def get_media_file_path(instance, filename):
    """動態產生 001 媒體檔的儲存路徑"""
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    tax_id = instance.year_record.client.tax_id or 'unknown_client'
    year = instance.year_record.year
    return f'income_tax/media_data/{tax_id}/{year}/{new_filename}'


class IncomeTaxMediaData(BaseModel):
    """
    所得稅申報書媒體檔 (001) 解析資料
    與 IncomeTaxYear 為 OneToOne 關係，每個年度最多一筆。
    上傳 001 檔後，由 parser 解析並存入結構化欄位。
    """
    year_record = models.OneToOneField(
        IncomeTaxYear,
        on_delete=models.CASCADE,
        related_name='media_data',
        verbose_name=_('所屬年度'),
    )

    # ── 原始檔案 ──
    raw_file = models.FileField(
        _('原始 001 檔'),
        upload_to=get_media_file_path,
        blank=True, null=True,
    )
    parsed_at = models.DateTimeField(_('解析時間'), null=True, blank=True)

    # ============================================================
    # 解析後的結構化欄位（核心）
    # ============================================================

    # ── 基本資訊 ──
    industry_code = models.CharField(
        _('行業代號'), max_length=20, blank=True,
    )
    industry_name = models.CharField(
        _('行業名稱'), max_length=100, blank=True,
    )

    # ── 損益資料 ──
    gross_revenue = models.DecimalField(
        _('營業收入淨額'), max_digits=15, decimal_places=0, default=0,
    )
    cost_of_goods = models.DecimalField(
        _('營業成本'), max_digits=15, decimal_places=0, default=0,
    )
    gross_profit = models.DecimalField(
        _('營業毛利'), max_digits=15, decimal_places=0, default=0,
    )
    operating_expenses = models.DecimalField(
        _('營業費用'), max_digits=15, decimal_places=0, default=0,
    )
    net_operating_income = models.DecimalField(
        _('營業淨利'), max_digits=15, decimal_places=0, default=0,
    )
    non_operating_income = models.DecimalField(
        _('營業外收入'), max_digits=15, decimal_places=0, default=0,
    )
    non_operating_expense = models.DecimalField(
        _('營業外支出'), max_digits=15, decimal_places=0, default=0,
    )

    # ── 稅額計算 ──
    pre_tax_income = models.DecimalField(
        _('稅前淨利'), max_digits=15, decimal_places=0, default=0,
    )
    taxable_income = models.DecimalField(
        _('課稅所得額'), max_digits=15, decimal_places=0, default=0,
    )
    annual_tax = models.DecimalField(
        _('應納稅額'), max_digits=15, decimal_places=0, default=0,
    )
    provisional_paid = models.DecimalField(
        _('暫繳稅額'), max_digits=15, decimal_places=0, default=0,
    )
    withholding_paid = models.DecimalField(
        _('扣繳稅額'), max_digits=15, decimal_places=0, default=0,
    )
    self_pay = models.DecimalField(
        _('應自行繳納稅額'), max_digits=15, decimal_places=0, default=0,
    )

    # ── 未分配盈餘 ──
    undistributed_earnings = models.DecimalField(
        _('未分配盈餘'), max_digits=15, decimal_places=0, default=0,
    )
    undistributed_surtax = models.DecimalField(
        _('未分配盈餘加徵'), max_digits=15, decimal_places=0, default=0,
    )

    # ── 完整原始解析資料（JSON 備份） ──
    raw_parsed_data = models.JSONField(
        _('完整解析原始資料'),
        default=dict,
        blank=True,
        help_text=_('001 檔解析後的完整 key-value 資料，供日後擴充欄位使用'),
    )

    class Meta:
        verbose_name = _('申報書媒體檔資料')
        verbose_name_plural = _('申報書媒體檔資料')

    def __str__(self):
        return f"{self.year_record} - 媒體檔資料"

    @property
    def is_parsed(self):
        """是否已完成解析"""
        return self.parsed_at is not None
