from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import CharWidget, ForeignKeyWidget
from simple_history.admin import SimpleHistoryAdmin
from .models import Customer, Contact, ServiceItem


# ──────────────────────────────────────────────
# Resource：定義 Customer 的匯入/匯出欄位對應
# ──────────────────────────────────────────────
class CustomerResource(resources.ModelResource):
    """
    Customer 匯入/匯出 Resource。
    - 以「統一編號 (tax_id)」作為比對 key，若已存在則更新（upsert）。
    - 若 tax_id 為空，則以「公司名稱 (name)」作為備用比對 key。
    - 匯入欄位對應中文標頭，方便使用者填寫 Excel。
    """

    # 明確宣告欄位以設定中文 column_name（作為 Excel 標頭）
    tax_id = fields.Field(
        attribute='tax_id',
        column_name='統一編號',
        widget=CharWidget(),
    )
    name = fields.Field(
        attribute='name',
        column_name='公司名稱',
        widget=CharWidget(),
    )
    source = fields.Field(
        attribute='source',
        column_name='客戶來源',  # ESTABLISHED / TRANSFERRED
        widget=CharWidget(),
    )
    contact_person = fields.Field(
        attribute='contact_person',
        column_name='聯絡人',
        widget=CharWidget(),
    )
    phone = fields.Field(
        attribute='phone',
        column_name='電話號碼',
        widget=CharWidget(),
    )
    mobile = fields.Field(
        attribute='mobile',
        column_name='手機號碼',
        widget=CharWidget(),
    )
    email = fields.Field(
        attribute='email',
        column_name='Email',
        widget=CharWidget(),
    )
    registered_zip = fields.Field(
        attribute='registered_zip',
        column_name='登記地址郵遞區號',
        widget=CharWidget(),
    )
    registered_address = fields.Field(
        attribute='registered_address',
        column_name='登記地址',
        widget=CharWidget(),
    )
    correspondence_zip = fields.Field(
        attribute='correspondence_zip',
        column_name='通訊地址郵遞區號',
        widget=CharWidget(),
    )
    correspondence_address = fields.Field(
        attribute='correspondence_address',
        column_name='通訊地址',
        widget=CharWidget(),
    )
    bank_account_last5 = fields.Field(
        attribute='bank_account_last5',
        column_name='帳號後五碼',
        widget=CharWidget(),
    )
    labor_ins_code = fields.Field(
        attribute='labor_ins_code',
        column_name='勞保代號',
        widget=CharWidget(),
    )
    health_ins_code = fields.Field(
        attribute='health_ins_code',
        column_name='健保代號',
        widget=CharWidget(),
    )
    line_id = fields.Field(
        attribute='line_id',
        column_name='LineID',
        widget=CharWidget(),
    )
    room_id = fields.Field(
        attribute='room_id',
        column_name='RoomID',
        widget=CharWidget(),
    )
    notes = fields.Field(
        attribute='notes',
        column_name='備註',
        widget=CharWidget(),
    )

    class Meta:
        model = Customer
        # 以 tax_id 為 upsert key（若 tax_id 非空則比對更新，否則新建）
        import_id_fields = ['tax_id']
        # 排除系統自動管理的欄位
        exclude = ('id', 'created_at', 'updated_at', 'is_deleted', 'history')
        # 匯入時若資料庫已存在相同 tax_id，更新而非新增
        skip_unchanged = True
        report_skipped = True
        # 使用軟刪除管理器以外的預設 manager，避免匯入時找不到已軟刪除的資料
        use_transactions = True

    def get_queryset(self):
        """匯入時查詢全部資料（包含軟刪除），避免重複新增"""
        return self._meta.model._default_manager.all()

    def before_import_row(self, row, row_number=None, **kwargs):
        """
        匯入前資料清洗：
        - 去除前後空白
        - 若 tax_id 空白則清為 None（避免空字串造成 upsert 衝突）
        """
        for key in row:
            if isinstance(row[key], str):
                row[key] = row[key].strip() or None
        # 確保空字串的 tax_id 視為 None
        if not row.get('統一編號'):
            row['統一編號'] = None


# ──────────────────────────────────────────────
# Admin：Customer
# ──────────────────────────────────────────────
@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    """
    ImportExportModelAdmin 必須排在 SimpleHistoryAdmin 之前（MRO 順序）。
    """
    resource_classes = [CustomerResource]

    list_display = ('name', 'tax_id', 'contact_person', 'phone', 'source', 'is_deleted', 'created_at')
    search_fields = ('name', 'tax_id', 'contact_person', 'phone', 'mobile', 'email')
    list_filter = ('is_deleted', 'source', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['soft_delete_action', 'restore_action']

    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'tax_id', 'source', 'line_id', 'room_id', 'is_deleted')
        }),
        ('聯絡資訊', {
            'fields': ('contact_person', 'phone', 'mobile', 'email')
        }),
        ('地址資訊', {
            'fields': ('registered_zip', 'registered_address', 'correspondence_zip', 'correspondence_address')
        }),
        ('帳務資訊', {
            'fields': ('bank_account_last5', 'labor_ins_code', 'health_ins_code')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.action(description='標記為刪除 (Soft Delete)')
    def soft_delete_action(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'{updated} 筆資料已標記為刪除。')

    @admin.action(description='復原刪除 (Restore)')
    def restore_action(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'{updated} 筆資料已復原。')


# ──────────────────────────────────────────────
# Resource：Contact 匯入/匯出
# ──────────────────────────────────────────────
class ContactResource(resources.ModelResource):
    customer = fields.Field(
        attribute='customer',
        column_name='客戶統一編號',
        widget=ForeignKeyWidget(Customer, field='tax_id'),
    )
    customer_name = fields.Field(column_name='客戶名稱', readonly=True)
    name = fields.Field(attribute='name', column_name='姓名', widget=CharWidget())
    phone = fields.Field(attribute='phone', column_name='電話', widget=CharWidget())
    mobile = fields.Field(attribute='mobile', column_name='手機', widget=CharWidget())
    fax = fields.Field(attribute='fax', column_name='傳真', widget=CharWidget())
    email = fields.Field(attribute='email', column_name='Email', widget=CharWidget())
    address = fields.Field(attribute='address', column_name='通訊地址', widget=CharWidget())
    tax_id = fields.Field(attribute='tax_id', column_name='統一編號', widget=CharWidget())
    notes = fields.Field(attribute='notes', column_name='備註', widget=CharWidget())

    class Meta:
        model = Contact
        import_id_fields = ['id']
        exclude = ('created_at', 'updated_at', 'is_deleted', 'history')
        skip_unchanged = True
        report_skipped = True
        use_transactions = True

    def dehydrate_customer_name(self, obj):
        return obj.customer.name if obj.customer else ''

    def before_import_row(self, row, _row_number=None, **kwargs):
        # 空字串的 id 視為 None，讓匯入判斷為新建
        if not row.get('id'):
            row['id'] = None


# ──────────────────────────────────────────────
# Admin：Contact
# ──────────────────────────────────────────────
@admin.register(Contact)
class ContactAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_classes = [ContactResource]
    list_display = ('name', 'customer', 'phone', 'mobile', 'email', 'is_deleted')
    search_fields = ('name', 'customer__name', 'phone', 'mobile', 'email')
    list_filter = ('is_deleted', 'customer',)
    autocomplete_fields = ['customer']
    actions = ['soft_delete_action', 'restore_action']

    @admin.action(description='標記為刪除 (Soft Delete)')
    def soft_delete_action(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'{updated} 筆資料已標記為刪除。')

    @admin.action(description='復原刪除 (Restore)')
    def restore_action(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'{updated} 筆資料已復原。')


# ──────────────────────────────────────────────
# Admin：ServiceItem
# ──────────────────────────────────────────────
@admin.register(ServiceItem)
class ServiceItemAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ('service_id', 'name', 'department', 'reference_fee',
                    'is_company_law_22_1', 'is_money_laundering_check',
                    'is_business_entity_change', 'is_shareholder_list_change')
    list_filter = ('department',)
    search_fields = ('service_id', 'name')
    readonly_fields = ('service_id',)
    ordering = ('service_id',)

