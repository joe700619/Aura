from django import forms
from .models import Progress, ClientAssessment, CaseAssessment, Shareholder, EquityTransaction, ShareholderRegister, CompanyFiling, FilingHistory
from django.utils.translation import gettext_lazy as _
from core.widgets import ModalSelectWidget

class ProgressForm(forms.ModelForm):
    CASE_TYPE_CHOICES = [
        ('setup', '設立'),
        ('capital_increase', '增資'),
        ('equity_change', '股權異動'),
        ('business_change', '營業人變更'),
    ]

    case_type = forms.MultipleChoiceField(
        choices=CASE_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500',
        }),
        required=False,
        label=_('案件種類')
    )

    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )

    search_contact = forms.CharField(
        label=_('搜尋聯絡人'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/contacts/search/progress/')
    )

    class Meta:
        model = Progress
        fields = [
            'unified_business_no', 'company_name', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address',
            'progress_status', 'mandate_return', 'acceptance_date', 'case_type',
            'note', 'quotation_data', 'cost_sharing_data', 'is_posted'
        ]
        widgets = {
            'is_posted': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'quotation_data': forms.HiddenInput(),
            'cost_sharing_data': forms.HiddenInput(),
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'line_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'room_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'main_contact': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'mobile': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'progress_status': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'mandate_return': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'acceptance_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.company_name:
            self.fields['search_customer'].widget.button_label = self.instance.company_name

    def clean_case_type(self):
        return self.cleaned_data['case_type']

class ClientAssessmentForm(forms.ModelForm):
    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )

    search_contact = forms.CharField(
        label=_('搜尋聯絡人'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/contacts/search/progress/')
    )

    # Boolean fields with Yes/No choices
    YES_NO_CHOICES = [
        (True, '是'),
        (False, '否'),
    ]
    is_gov_agency = forms.TypedChoiceField(label=_('是否為我國政府機關及公營事業機構'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_foreign_gov = forms.TypedChoiceField(label=_('是否為外國政府機關'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_public_company = forms.TypedChoiceField(label=_('是否為我國公開發行公司及其子公司'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_foreign_listed_subsidiary = forms.TypedChoiceField(label=_('是否為於國外掛牌並依掛牌所在地規定，應揭露其主要股東之股票上市、上櫃公司其子公司'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_regulated_financial_inst = forms.TypedChoiceField(label=_('是否為受我國監理之金融機構及其管理之投資工具'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_foreign_regulated_inst = forms.TypedChoiceField(label=_('是否設立於我國境外，且所受監理規範與防制洗錢金融行動工作組織（FATF）所定防制洗錢及打擊資恐標準一致之金融機構，及該金融機構管理之投資工具'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_gov_fund = forms.TypedChoiceField(label=_('是否為我國政府機關主管之基金'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)
    is_employee_trust = forms.TypedChoiceField(label=_('是否為員工持股信託、員工福利儲蓄信託'), choices=YES_NO_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True', required=False)

    class Meta:
        model = ClientAssessment
        fields = [
            'company_name', 'unified_business_no', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address',
            'risk_level',
            'is_gov_agency', 'is_foreign_gov', 'is_public_company',
            'is_foreign_listed_subsidiary', 'is_regulated_financial_inst',
            'is_foreign_regulated_inst', 'is_gov_fund', 'is_employee_trust'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'readonly': 'readonly'}),
            'line_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'room_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'main_contact': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'mobile': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'risk_level': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.company_name:
            self.fields['search_customer'].widget.button_label = self.instance.company_name

class CaseAssessmentForm(forms.ModelForm):
    class Meta:
        model = CaseAssessment
        fields = ['date', 'registration_no', 'risk_level', 'is_accepted', 'is_completed', 'needs_reporting', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'registration_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'risk_level': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'is_accepted': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'needs_reporting': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_accepted'].required = False
        self.fields['is_completed'].required = False
        self.fields['needs_reporting'].required = False

CaseAssessmentFormSet = forms.inlineformset_factory(
    ClientAssessment,
    CaseAssessment,
    form=CaseAssessmentForm,
    extra=1,
    can_delete=True
)

class CaseAssessmentCRUDForm(forms.ModelForm):
    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/registration/api/client-assessment-search/')
    )

    search_contact = forms.CharField(
        label=_('搜尋聯絡人'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/contacts/search/progress/')
    )

    search_registration_no = forms.CharField(
        label=_('搜尋登記進度'),
        required=False,
        widget=ModalSelectWidget(search_url='/registration/api/progress-search/')
    )



    class Meta:
        model = CaseAssessment
        fields = [
            'company_name', 'unified_business_no', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address',
            'date', 'registration_no', 'risk_level',
            'is_accepted', 'is_completed', 'needs_reporting',
            'transaction_50', 'transaction_51', 'transaction_52', 'transaction_53',
            'transaction_54', 'transaction_55', 'transaction_56', 'transaction_57',
            'transaction_58', 'transaction_59',
            'warning_1', 'warning_2', 'warning_3', 'warning_4',
            'warning_5', 'warning_6', 'warning_7', 'warning_8',
            'appendix_1', 'appendix_1_note',
            'appendix_2', 'appendix_2_note',
            'appendix_3', 'appendix_3_note',
            'appendix_4', 'appendix_4_note',
            'note'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'readonly': 'readonly'}),
            'line_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'room_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'main_contact': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'mobile': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'registration_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'risk_level': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'is_accepted': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'needs_reporting': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'warning_5': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'warning_6': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'warning_7': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'warning_8': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            
            # Appendix widgets
            'appendix_1': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'appendix_2': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'appendix_3': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'appendix_4': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}),
            'appendix_1_note': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'appendix_2_note': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'appendix_3_note': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'appendix_4_note': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),

            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_accepted'].required = False
        self.fields['is_completed'].required = False
        self.fields['needs_reporting'].required = False
        if self.instance and self.instance.pk and self.instance.company_name:
            self.fields['search_customer'].widget.button_label = self.instance.company_name

class ShareholderForm(forms.ModelForm):
    class Meta:
        model = Shareholder
        fields = ['name', 'id_number', 'nationality', 'birthday', 'address', 'is_active', 'note']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'id_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'nationality': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'birthday': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'is_active': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update nationality choices to display "CODE Label"
        nationality_field = self.fields['nationality']
        nationality_field.choices = [
            (code, f"{code} {label}") for code, label in Shareholder.Nationality.choices
        ]

    def clean_id_number(self):
        id_number = self.cleaned_data['id_number']
        # Check if ID number already exists, excluding current instance
        qs = Shareholder.objects.filter(id_number=id_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError(_('此身分證字號已經存在'))
        
        return id_number

class EquityTransactionForm(forms.ModelForm):
    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )

    search_shareholder = forms.CharField(
        label=_('搜尋股東'),
        required=False,
        widget=ModalSelectWidget(search_url='/registration/api/shareholder-search/')
    )

    search_shareholder_register = forms.CharField(
        label=_('搜尋公司 (股東名簿)'),
        required=False,
        widget=ModalSelectWidget(search_url='/registration/api/shareholder-register-search/')
    )

    display_company_name = forms.CharField(
        label=_('公司名稱'),
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'id': 'id_display_company_name', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-100 text-slate-500 text-sm'})
    )

    display_unified_business_no = forms.CharField(
        label=_('統一編號'),
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'id': 'id_display_unified_business_no', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-100 text-slate-500 text-sm'})
    )

    class Meta:
        model = EquityTransaction
        fields = [
            'shareholder_register',
            'shareholder_name', 'shareholder_id_number', 'shareholder_address',
            'transaction_date', 'organization_type', 'transaction_reason',
            'stock_type', 'share_count', 'unit_price', 'total_amount',
            'registration_no', 'is_completed',
            'note'
        ]

        widgets = {
            'shareholder_register': forms.HiddenInput(attrs={'id': 'id_shareholder_register'}),
            # Card 2: Shareholder Info
            'shareholder_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'shareholder_id_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'shareholder_address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),

            # Card 3: Transaction Info
            'transaction_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'organization_type': forms.Select(attrs={'id': 'id_organization_type', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'transaction_reason': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'stock_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'share_count': forms.NumberInput(attrs={'id': 'id_share_count', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'unit_price': forms.NumberInput(attrs={'id': 'id_unit_price', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'id': 'id_total_amount', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'step': '0.01', 'readonly': 'readonly'}),

            'registration_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'is_completed': forms.Select(choices=[('False', '待處理'), ('True', '已完成')], attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shareholder_register'].required = True
        self.fields['is_completed'].required = False
        if self.instance and self.instance.pk and self.instance.shareholder_name:
            self.fields['search_shareholder'].widget.button_label = self.instance.shareholder_name

EquityTransactionFormSet = forms.inlineformset_factory(
    ShareholderRegister,
    EquityTransaction,
    form=EquityTransactionForm,
    extra=1,
    can_delete=True
)

class ShareholderRegisterForm(forms.ModelForm):
    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )

    class Meta:
        model = ShareholderRegister
        fields = [
            'company_name', 'unified_business_no', 'line_id', 'room_id', 'service_status', 'completion_status'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'line_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'room_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'service_status': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'completion_status': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.company_name:
            self.fields['search_customer'].widget.button_label = self.instance.company_name

class CompanyFilingForm(forms.ModelForm):
    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )

    search_contact = forms.CharField(
        label=_('搜尋聯絡人'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/contacts/search/progress/')
    )

    class Meta:
        model = CompanyFiling
        fields = [
            'unified_business_no', 'company_name', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address',
            'fee', 'filing_method', 'account', 'password', 'health_insurance_card_no', 
            'note'
        ]
        widgets = {
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'line_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'room_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'main_contact': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'mobile': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'fee': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'filing_method': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'account': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'password': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'health_insurance_card_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }

class FilingHistoryForm(forms.ModelForm):
    class Meta:
        model = FilingHistory
        fields = ['year', 'category', 'filing_date', 'registration_no', 'is_completed']
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'category': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'filing_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'registration_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-green-600 focus:ring-green-500 border-slate-300 rounded cursor-pointer'}),
        }

FilingHistoryFormSet = forms.inlineformset_factory(
    CompanyFiling,
    FilingHistory,
    form=FilingHistoryForm,
    extra=0,
    can_delete=True
)

class VATEntityChangeForm(forms.ModelForm):
    from .models import VATEntityChange
    
    case_types = forms.MultipleChoiceField(
        choices=VATEntityChange.CASE_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500',
        }),
        required=False,
        label=_('案件種類')
    )

    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )

    class Meta:
        from .models import VATEntityChange
        model = VATEntityChange
        fields = [
            'unified_business_no', 'company_name', 'tax_id', 'registered_address',
            'assistant_name', 'email',
            'case_types', 'registration_no', 'is_completed', 'closed_at',
            'note'
        ]
        widgets = {
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'registered_address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'assistant_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'registration_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-100 text-slate-500 text-sm', 'readonly': 'readonly'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-green-600 focus:ring-green-500 border-slate-300 rounded cursor-pointer'}),
            'closed_at': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_completed'].required = False
        self.fields['registration_no'].required = False
        if self.instance and self.instance.pk and self.instance.company_name:
            self.fields['search_customer'].widget.button_label = self.instance.company_name
