from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

# 各「案件種類」所需準備文件對應表。
# 資料來源：Aura_discussion/營業人變更須要資料.md（由事務所維護）。
# key 對應 VATEntityChange.CASE_TYPE_CHOICES 的 value；多選時前端會取聯集去重。
CASE_TYPE_DOCUMENTS = {
    'setup': ['申請書', '負責人身分證影本', '公司設立變更登表影本', '房屋稅稅單影本', '租約影本(註1)'],
    'rep_change': ['申請書', '負責人身分證影本', '公司設立變更登表影本'],
    'name_change': ['申請書', '公司設立變更登表影本'],
    'addr_change': ['申請書', '公司設立變更登表影本', '房屋稅稅單影本', '租約影本(註1)'],
    'item_change': ['申請書', '公司設立變更登表影本', '註記營業比例(註2)'],
    'org_change': ['申請書', '公司設立變更登表影本'],
    'cap_increase': ['申請書', '公司設立變更登表影本'],
    'cap_decrease': ['申請書', '公司設立變更登表影本'],
    'tax_unit_to_vat': ['申請書', '負責人身分證影本', '公司設立變更登表影本'],
    'online_sales_change': ['申請書', '公司設立變更登表影本'],
    'other': ['申請書'],
}

# 文件附註說明（對應上表文件名稱後的 (註n) 標記）。
DOCUMENT_NOTES = [
    '註1：國稅局不太收使用同意書，盡量檢附租約影本。',
    '註2：申請營業項目變更時，請於備註欄填寫各營業項目占收入比例（大約估計）。',
]


class VATEntityChange(BaseModel):
    # 1. Basic Data
    unified_business_no = models.CharField(_('統一編號'), max_length=20, blank=True)
    company_name = models.CharField(_('公司名稱'), max_length=255, blank=True)
    tax_id = models.CharField(_('稅籍編號'), max_length=50, blank=True)
    registered_address = models.CharField(_('登記地址'), max_length=255, blank=True)

    # 由 GCIS 商工登記帶入的快照（申請當下凝結，不隨日後變動）。
    # 金額用 BigInteger：資本額可達數千億，超過一般 IntegerField 上限。
    representative_name = models.CharField(_('負責人姓名'), max_length=100, blank=True)
    capital_stock_amount = models.BigIntegerField(_('資本總額'), null=True, blank=True)
    paid_in_capital_amount = models.BigIntegerField(_('實收資本額'), null=True, blank=True)

    # 2. Contact Data
    assistant_name = models.CharField(_('助理人員'), max_length=100, blank=True)
    email = models.EmailField(_('Email'), blank=True)

    # 3. Other
    CASE_TYPE_CHOICES = [
        ('setup', _('設立')),
        ('rep_change', _('負責人變更')),
        ('name_change', _('名稱變更')),
        ('addr_change', _('所在地變更')),
        ('item_change', _('營業項目變更')),
        ('org_change', _('組織變更')),
        ('cap_increase', _('增資變更')),
        ('cap_decrease', _('減資變更')),
        ('tax_unit_to_vat', _('扣繳單位變更為營業人')),
        ('online_sales_change', _('網路銷售資訊變更')),
        ('other', _('其他')),
    ]
    case_types = models.JSONField(_('案件種類'), default=list, blank=True)
    registration_no = models.CharField(_('登記單號'), max_length=20, blank=True)
    is_completed = models.BooleanField(_('完成狀態'), default=False)
    closed_at = models.DateField(_('結案日期'), null=True, blank=True)

    # 4. Note
    note = models.TextField(_('備註'), blank=True, null=True)

    class Meta:
        verbose_name = _('營業人變更登記')
        verbose_name_plural = _('營業人變更登記')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.registration_no} - {self.company_name}"
