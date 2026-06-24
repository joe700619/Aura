from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, BooleanWidget
from .models import EquityTransaction, ShareholderRegister

_ORG_TYPE_MAP = {
    '有限公司': 'LTD',
    '股份有限公司': 'CORP',
}

_REASON_MAP = {
    '設立': 'SETUP',
    '增資': 'CAPITAL_INCREASE',
    '減資': 'CAPITAL_REDUCTION',
    '買入': 'BUY',
    '賣出': 'SELL',
    '贈與': 'GIFT',
    '受贈': 'BEQUEST',
    '合併增加': 'MERGER_INCREASE',
    '合併減少': 'MERGER_DECREASE',
    '分割增加': 'SPLIT_INCREASE',
    '分割減少': 'SPLIT_DECREASE',
    '其他增加': 'OTHER_INCREASE',
    '其他減少': 'OTHER_DECREASE',
}

_STOCK_TYPE_MAP = {
    '普通股': 'COMMON',
    '特別股': 'PREFERRED',
}


class EquityTransactionResource(resources.ModelResource):
    """
    匯入時：用「統一編號」查找對應的股東名簿；選單欄位接受中文標籤或英文代碼。
    匯出時：公司名稱、組織種類、交易事由、股票種類均以中文顯示。
    """

    shareholder_register = fields.Field(
        column_name='統一編號',
        attribute='shareholder_register',
        widget=ForeignKeyWidget(ShareholderRegister, field='unified_business_no'),
    )
    company_name = fields.Field(column_name='公司名稱', readonly=True)
    shareholder_name = fields.Field(column_name='姓名', attribute='shareholder_name')
    shareholder_id_number = fields.Field(column_name='身份證字號', attribute='shareholder_id_number')
    shareholder_address = fields.Field(column_name='地址', attribute='shareholder_address')
    transaction_date = fields.Field(column_name='交易日期', attribute='transaction_date')
    organization_type = fields.Field(column_name='組織種類', attribute='organization_type')
    transaction_reason = fields.Field(column_name='交易事由', attribute='transaction_reason')
    stock_type = fields.Field(column_name='股票種類', attribute='stock_type')
    share_count = fields.Field(column_name='股數', attribute='share_count')
    unit_price = fields.Field(column_name='單價', attribute='unit_price')
    total_amount = fields.Field(column_name='合計', attribute='total_amount')
    registration_no = fields.Field(column_name='登記案件編號', attribute='registration_no')
    is_completed = fields.Field(
        column_name='是否完成',
        attribute='is_completed',
        widget=BooleanWidget(),
    )
    note = fields.Field(column_name='備註', attribute='note')

    class Meta:
        model = EquityTransaction
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = False
        exclude = ('is_deleted', 'created_at', 'updated_at')
        export_order = (
            'id',
            'shareholder_register',
            'company_name',
            'shareholder_name',
            'shareholder_id_number',
            'shareholder_address',
            'transaction_date',
            'organization_type',
            'transaction_reason',
            'stock_type',
            'share_count',
            'unit_price',
            'total_amount',
            'registration_no',
            'is_completed',
            'note',
        )

    def dehydrate_company_name(self, obj):
        return obj.shareholder_register.company_name if obj.shareholder_register else ''

    def dehydrate_organization_type(self, obj):
        return obj.get_organization_type_display()

    def dehydrate_transaction_reason(self, obj):
        return obj.get_transaction_reason_display()

    def dehydrate_stock_type(self, obj):
        return obj.get_stock_type_display()

    def before_import_row(self, row, **kwargs):
        for col, mapping in [
            ('組織種類', _ORG_TYPE_MAP),
            ('交易事由', _REASON_MAP),
            ('股票種類', _STOCK_TYPE_MAP),
        ]:
            val = row.get(col)
            if val in mapping:
                row[col] = mapping[val]
