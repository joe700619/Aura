from django.contrib import admin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, CharWidget

from .models import (
    BookkeepingClient,
    GroupInvoice,
    ConvenienceBagLog,
    AccountingBookLog,
    TaxFilingSetting,
    TaxFilingYear,
    TaxFilingPeriod,
    IndustryTaxRate,
    ClientBill,
    BusinessRegistration,
    BusinessRegistrationDocument,
    ServiceRemuneration,
    ServiceRemunerationTaxRate,
    NHIConfig,
    TaxUnit,
)
from modules.hr.models import Employee
from core.auth.models import User


class BookkeepingClientResource(resources.ModelResource):
    tax_id = fields.Field(attribute='tax_id', column_name='統一編號', widget=CharWidget())
    name = fields.Field(attribute='name', column_name='公司名稱', widget=CharWidget())
    contact_person = fields.Field(attribute='contact_person', column_name='聯絡人', widget=CharWidget())
    phone = fields.Field(attribute='phone', column_name='電話', widget=CharWidget())
    mobile = fields.Field(attribute='mobile', column_name='手機', widget=CharWidget())
    correspondence_address = fields.Field(attribute='correspondence_address', column_name='通訊地址', widget=CharWidget())
    registered_address = fields.Field(attribute='registered_address', column_name='登記地址', widget=CharWidget())
    acceptance_status = fields.Field(attribute='acceptance_status', column_name='承接狀態', widget=CharWidget())
    billing_status = fields.Field(attribute='billing_status', column_name='帳務狀態', widget=CharWidget())
    service_type = fields.Field(attribute='service_type', column_name='服務類型', widget=CharWidget())
    client_source = fields.Field(attribute='client_source', column_name='客戶來源', widget=CharWidget())
    bookkeeping_assistant = fields.Field(
        attribute='bookkeeping_assistant',
        column_name='記帳助理員工編號',
        widget=ForeignKeyWidget(Employee, field='employee_number'),
    )
    group_assistant = fields.Field(
        attribute='group_assistant',
        column_name='組別助理員工編號',
        widget=ForeignKeyWidget(Employee, field='employee_number'),
    )

    class Meta:
        model = BookkeepingClient
        import_id_fields = ['tax_id']
        exclude = ('id', 'created_at', 'updated_at', 'is_deleted', 'history', 'customer')
        skip_unchanged = True
        report_skipped = True
        use_transactions = True

    def get_queryset(self):
        return self._meta.model._default_manager.all()

    def before_import_row(self, row, _row_number=None, **kwargs):
        for key in list(row.keys()):
            if isinstance(row[key], str):
                row[key] = row[key].strip() or None


DEFAULT_PORTAL_PASSWORD = 'Aura@2026'


@admin.register(BookkeepingClient)
class BookkeepingClientAdmin(ImportExportModelAdmin):
    resource_classes = [BookkeepingClientResource]
    list_display = ('name', 'tax_id', 'acceptance_status', 'billing_status', 'service_type', 'portal_account_status', 'is_deleted')
    list_filter = ('is_deleted', 'acceptance_status', 'billing_status', 'service_type', 'client_source')
    search_fields = ('name', 'tax_id')
    actions = ['restore_clients', 'batch_create_portal_accounts']
    readonly_fields = ('portal_account_info',)

    def get_queryset(self, _request):
        return self.model._default_manager.all()

    # ── Portal 帳號狀態（列表欄位）─────────────────────────────
    @admin.display(description='Portal 帳號')
    def portal_account_status(self, obj):
        u = obj.user
        if not u:
            return format_html('<span style="color:#999;">未建立</span>')
        if not u.is_active:
            return format_html('<span style="color:#e53e3e;">已停用 ({})</span>', u.username)
        return format_html('<span style="color:#38a169;">✓ {} </span>', u.username)

    # ── Portal 帳號詳情（change form 欄位）──────────────────────
    @admin.display(description='Portal 帳號管理')
    def portal_account_info(self, obj):
        if not obj.pk:
            return '請先儲存後再管理 Portal 帳號。'
        u = obj.user
        base = reverse('admin:bookkeeping_bookkeepingclient_change', args=[obj.pk])
        if not u:
            create_url = reverse('admin:bookkeeping_client_portal_create', args=[obj.pk])
            return format_html(
                '<p style="color:#999;margin-bottom:8px;">尚未建立 Portal 帳號</p>'
                '<a href="{}" class="button default" style="margin-right:6px;">建立帳號（帳號：{}，密碼：{}）</a>',
                create_url, obj.tax_id or obj.pk, DEFAULT_PORTAL_PASSWORD,
            )
        status = '啟用中' if u.is_active else '<span style="color:#e53e3e;">已停用</span>'
        reset_url  = reverse('admin:bookkeeping_client_portal_reset',  args=[obj.pk])
        toggle_url = reverse('admin:bookkeeping_client_portal_toggle', args=[obj.pk])
        toggle_label = '停用帳號' if u.is_active else '啟用帳號'
        toggle_style = 'color:#e53e3e;' if u.is_active else 'color:#38a169;'
        return format_html(
            '<p><strong>帳號：</strong>{} &nbsp;|&nbsp; <strong>狀態：</strong>{}</p>'
            '<a href="{}" class="button default" style="margin-right:6px;">重設密碼（→ {}）</a>'
            '<a href="{}" class="button default" style="{}">{}</a>',
            u.username, format_html(status),
            reset_url, DEFAULT_PORTAL_PASSWORD,
            toggle_url, toggle_style, toggle_label,
        )

    fieldsets = (
        ('基本資料', {'fields': (
            'customer', 'name', 'tax_id', 'tax_registration_no', 'tax_authority_code',
            'acceptance_status', 'billing_status', 'service_type', 'client_source',
        )}),
        ('聯絡資訊', {'fields': (
            'contact_person', 'phone', 'mobile',
            'correspondence_address', 'registered_address',
        )}),
        ('Line / 通知', {'fields': (
            'line_id', 'room_id', 'notification_method',
        )}),
        ('申報設定', {'fields': (
            'send_invoice_method', 'send_merged_client_name',
            'receive_invoice_method', 'receive_merged_client_name',
        ), 'classes': ('collapse',)}),
        ('助理', {'fields': (
            'group_assistant', 'bookkeeping_assistant',
        ), 'classes': ('collapse',)}),
        ('其他', {'fields': (
            'notes', 'is_deleted',
        ), 'classes': ('collapse',)}),
    )

    def get_fieldsets(self, _request, obj=None):
        fs = list(self.fieldsets)
        if obj:
            fs.append(('Portal 客戶帳號', {'fields': ('portal_account_info',)}))
        return fs

    # ── 自訂 URL ────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/portal/create/',
                 self.admin_site.admin_view(self._portal_create),
                 name='bookkeeping_client_portal_create'),
            path('<int:pk>/portal/reset/',
                 self.admin_site.admin_view(self._portal_reset),
                 name='bookkeeping_client_portal_reset'),
            path('<int:pk>/portal/toggle/',
                 self.admin_site.admin_view(self._portal_toggle),
                 name='bookkeeping_client_portal_toggle'),
        ]
        return custom + urls

    def _portal_create(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk)
        if client.user:
            messages.warning(request, f'「{client.name}」已有 Portal 帳號 ({client.user.username})。')
        else:
            username = client.tax_id or str(pk)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': 'EXTERNAL', 'is_active': True},
            )
            if created:
                user.set_password(DEFAULT_PORTAL_PASSWORD)
                user.save()
            client.user = user
            client.save(update_fields=['user'])
            messages.success(request, f'已為「{client.name}」建立 Portal 帳號，帳號：{username}，密碼：{DEFAULT_PORTAL_PASSWORD}')
        return redirect(reverse('admin:bookkeeping_bookkeepingclient_change', args=[pk]))

    def _portal_reset(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk)
        if client.user:
            client.user.set_password(DEFAULT_PORTAL_PASSWORD)
            client.user.save()
            messages.success(request, f'已重設「{client.name}」的 Portal 密碼為：{DEFAULT_PORTAL_PASSWORD}')
        else:
            messages.error(request, '此客戶尚無 Portal 帳號。')
        return redirect(reverse('admin:bookkeeping_bookkeepingclient_change', args=[pk]))

    def _portal_toggle(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk)
        if client.user:
            client.user.is_active = not client.user.is_active
            client.user.save(update_fields=['is_active'])
            status = '啟用' if client.user.is_active else '停用'
            messages.success(request, f'已{status}「{client.name}」的 Portal 帳號。')
        else:
            messages.error(request, '此客戶尚無 Portal 帳號。')
        return redirect(reverse('admin:bookkeeping_bookkeepingclient_change', args=[pk]))

    # ── 批次建立帳號 action ──────────────────────────────────────
    @admin.action(description='批次建立 Portal 帳號（統一編號為帳號）')
    def batch_create_portal_accounts(self, request, queryset):
        created_count = 0
        skip_count = 0
        for client in queryset:
            if client.user:
                skip_count += 1
                continue
            username = client.tax_id or str(client.pk)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': 'EXTERNAL', 'is_active': True},
            )
            if created:
                user.set_password(DEFAULT_PORTAL_PASSWORD)
                user.save()
            client.user = user
            client.save(update_fields=['user'])
            created_count += 1
        self.message_user(request, f'已建立 {created_count} 個帳號，略過 {skip_count} 個（已有帳號）。')

    @admin.action(description='還原已刪除的記帳客戶')
    def restore_clients(self, request, queryset):
        updated = queryset.filter(is_deleted=True).update(is_deleted=False)
        self.message_user(request, f'已還原 {updated} 筆記帳客戶。')


@admin.register(GroupInvoice)
class GroupInvoiceAdmin(admin.ModelAdmin):
    list_display = ('client', 'invoice_type', 'quantity')
    list_filter = ('invoice_type',)


@admin.register(ConvenienceBagLog)
class ConvenienceBagLogAdmin(admin.ModelAdmin):
    list_display = ('client', 'date', 'quantity')


@admin.register(AccountingBookLog)
class AccountingBookLogAdmin(admin.ModelAdmin):
    list_display = ('client', 'date', 'year', 'cd_rom', 'sales_invoice_qty')
    list_filter = ('year', 'cd_rom')


@admin.register(TaxFilingSetting)
class TaxFilingSettingAdmin(ImportExportModelAdmin):
    list_display = ('client', 'form_type', 'filing_frequency', 'is_audited')
    list_filter = ('form_type', 'filing_frequency', 'is_audited')
    search_fields = ('client__name',)


@admin.register(TaxFilingYear)
class TaxFilingYearAdmin(ImportExportModelAdmin):
    list_display = ('client', 'year')
    list_filter = ('year',)
    search_fields = ('client__name',)


@admin.register(TaxFilingPeriod)
class TaxFilingPeriodAdmin(ImportExportModelAdmin):
    list_display = ('year_record', 'period_start_month', 'sales_amount', 'payable_tax', 'is_filed', 'filing_date')
    list_filter = ('is_filed', 'period_start_month')
    search_fields = ('year_record__client__name',)


@admin.register(ClientBill)
class ClientBillAdmin(admin.ModelAdmin):
    list_display = ('bill_no', 'client', 'year', 'month', 'bill_date', 'total_amount', 'status', 'is_ar_transferred', 'is_deleted')
    list_filter = ('is_deleted', 'status', 'is_ar_transferred', 'year')
    search_fields = ('bill_no', 'client__name', 'client__tax_id')
    actions = ['restore_bills']

    def get_queryset(self, _request):
        return self.model._default_manager.all()

    @admin.action(description='還原已刪除的帳單')
    def restore_bills(self, request, queryset):
        updated = queryset.filter(is_deleted=True).update(is_deleted=False)
        self.message_user(request, f'已還原 {updated} 筆帳單。')


class BusinessRegistrationDocumentInline(admin.TabularInline):
    model = BusinessRegistrationDocument
    extra = 0
    fields = ('document_date', 'name', 'file')


@admin.register(BusinessRegistration)
class BusinessRegistrationAdmin(admin.ModelAdmin):
    list_display = ('client',)
    search_fields = ('client__name', 'client__tax_id')
    inlines = [BusinessRegistrationDocumentInline]


@admin.register(ServiceRemunerationTaxRate)
class ServiceRemunerationTaxRateAdmin(ImportExportModelAdmin):
    list_display = ('code', 'label', 'withholding_rate', 'expense_rate', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('code', 'label')
    ordering = ('sort_order', 'code')


@admin.register(NHIConfig)
class NHIConfigAdmin(admin.ModelAdmin):
    list_display = ('threshold', 'rate')


@admin.register(ServiceRemuneration)
class ServiceRemunerationAdmin(admin.ModelAdmin):
    list_display = (
        'recipient_name', 'client', 'income_category', 'amount',
        'withholding_tax', 'supplementary_premium',
        'confirmation_status', 'payment_status', 'filing_date',
    )
    list_filter = ('income_category', 'confirmation_status', 'payment_status', 'nationality')
    search_fields = ('recipient_name', 'id_number', 'client__name')
    readonly_fields = ('confirm_token', 'withholding_tax', 'supplementary_premium', 'actual_payment')


@admin.register(IndustryTaxRate)
class IndustryTaxRateAdmin(ImportExportModelAdmin):
    list_display = ('industry_code', 'industry_name', 'applicable_year', 'book_review_profit_rate', 'net_profit_rate', 'income_standard')
    search_fields = ('industry_code', 'industry_name')
    list_filter = ('applicable_year',)
    ordering = ('-applicable_year', 'industry_code')


class TaxUnitResource(resources.ModelResource):
    city_id     = fields.Field(attribute='city_id',     column_name='city_id')
    unit_code   = fields.Field(attribute='unit_code',   column_name='unit_code')
    dept_id     = fields.Field(attribute='dept_id',     column_name='dept_id')
    unit_name   = fields.Field(attribute='unit_name',   column_name='unit_name')
    bureau_name = fields.Field(attribute='bureau_name', column_name='bureau_name')

    class Meta:
        model = TaxUnit
        import_id_fields = ['city_id', 'unit_code']
        fields = ('city_id', 'unit_code', 'dept_id', 'unit_name', 'bureau_name')
        skip_unchanged = True
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        header_map = {
            '城市代號': 'city_id',
            '稅籍單位代碼': 'unit_code',
            '稽徵所代號': 'dept_id',
            '單位名稱': 'unit_name',
            '國稅局名稱': 'bureau_name',
        }
        if dataset.headers:
            dataset.headers = [header_map.get(h, h) for h in dataset.headers]
        super().before_import(dataset, **kwargs)

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not (instance.city_id or '').strip() or not (instance.unit_code or '').strip():
            return True
        return super().skip_row(instance, original, row, import_validation_errors)


@admin.register(TaxUnit)
class TaxUnitAdmin(ImportExportModelAdmin):
    resource_classes = [TaxUnitResource]
    list_display = ('city_id', 'unit_code', 'dept_id', 'unit_name', 'bureau_name')
    search_fields = ('unit_code', 'unit_name', 'city_id', 'bureau_name')
    ordering = ('city_id', 'unit_code')
