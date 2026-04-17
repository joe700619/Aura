from django import forms
from django.forms import inlineformset_factory
from core.widgets import ModalSelectWidget
from .models import Account, Voucher, VoucherDetail, Receivable, ReceivableFeeApportion, PaymentRecord, Collection, FixedAsset, PreCollection

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'category', 'auxiliary_type', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'category': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'auxiliary_type': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
        }

class VoucherForm(forms.ModelForm):
    voucher_no = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'readonly': 'readonly', 'placeholder': '(存檔後由系統自動產生)'}))
    creator_name = forms.CharField(label="編輯者", required=False, widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'readonly': 'readonly'}))

    class Meta:
        model = Voucher
        fields = ['date', 'voucher_no', 'description', 'status', 'source']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'status': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'source': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source'].required = True
        if not self.instance.pk:
            self.fields['source'].initial = 'MANUAL'

        if self.instance and self.instance.pk:
            if self.instance.created_by:
                self.initial['creator_name'] = self.instance.created_by.get_full_name() or self.instance.created_by.username
            else:
                self.initial['creator_name'] = '系統'
        else:
            self.initial['creator_name'] = '(存檔後產生)'

class VoucherDetailForm(forms.ModelForm):
    class Meta:
        model = VoucherDetail
        fields = ['account', 'debit', 'credit', 'company_id', 'department', 'project', 'remark']
        widgets = {
            'account': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm select2 account-select'}),
            'debit': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right debit-input', 'step': '1'}),
            'credit': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right credit-input', 'step': '1'}),
            'company_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'department': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'project': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'remark': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'DELETE': forms.CheckboxInput(attrs={'class': 'delete-checkbox hidden'}),
        }

VoucherDetailFormSet = inlineformset_factory(
    Voucher, 
    VoucherDetail, 
    form=VoucherDetailForm,
    extra=2,
    can_delete=True
)

class ReceivableForm(forms.ModelForm):
    search_customer = forms.CharField(
        label="搜尋客戶 (帶入基本資料)",
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/')
    )
    search_contact = forms.CharField(
        label="搜尋聯絡人 (帶入聯絡資料)",
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/contacts/search/progress/')
    )

    class Meta:
        model = Receivable
        fields = [
            'date', 'company_name', 'unified_business_no', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address', 'email',
            'assistant', 'assistant_email', 'remarks',
            'quotation_data', 'cost_sharing_data'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly', 'class': 'w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 text-slate-500 cursor-not-allowed text-sm'}),
            'company_name': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 text-slate-500 cursor-not-allowed text-sm'}),
            'unified_business_no': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 text-slate-500 cursor-not-allowed text-sm'}),
            'line_id': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 text-slate-500 cursor-not-allowed text-sm'}),
            'room_id': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 text-slate-500 cursor-not-allowed text-sm'}),
            'main_contact': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'mobile': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'assistant': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'assistant_email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'quotation_data': forms.HiddenInput(),
            'cost_sharing_data': forms.HiddenInput(),
        }

class ReceivableFeeApportionForm(forms.ModelForm):
    class Meta:
        model = ReceivableFeeApportion
        fields = ['employee', 'task_description', 'amount', 'ratio']
        widgets = {
            'employee': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'task_description': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right flex-1'}),
            'ratio': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right'}),
            'DELETE': forms.CheckboxInput(attrs={'class': 'delete-checkbox hidden'}),
        }

ReceivableFeeApportionFormSet = inlineformset_factory(
    Receivable,
    ReceivableFeeApportion,
    form=ReceivableFeeApportionForm,
    extra=1,
    can_delete=True
)

class PaymentRecordForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ['date', 'amount', 'remark']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right'}),
            'remark': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
        }

PaymentRecordFormSet = inlineformset_factory(
    Receivable,
    PaymentRecord,
    fields=['date', 'amount', 'remark'],
    extra=1,
    can_delete=True,
    widgets={
        'date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
        'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right payment-amount-input'}),
        'remark': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
    }
)


class CollectionForm(forms.ModelForm):
    search_receivable = forms.CharField(
        label="選擇應收帳款 (帶入基本資料)",
        required=False,
        widget=ModalSelectWidget(search_url='/accounting/api/receivables/search/')
    )

    class Meta:
        model = Collection
        fields = [
            'receivable', 'collection_no', 'date', 'method',
            'amount', 'tax', 'fee', 'allowance', 'total',
            'is_correction_needed', 'reporting_amount', 'remarks'
        ]
        widgets = {
            'receivable': forms.HiddenInput(),
            'collection_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'readonly': 'readonly', 'placeholder': '(自動產生)'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'method': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right calc-input', 'step': '1'}),
            'tax': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right calc-input', 'step': '1'}),
            'fee': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right calc-input', 'step': '1'}),
            'allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right calc-input', 'step': '1'}),
            'total': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right bg-slate-50', 'readonly': 'readonly', 'step': '1'}),
            'is_correction_needed': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
            'reporting_amount': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right', 'step': '1'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        }

    def _clean_integer_field(self, field_name):
        from decimal import Decimal, InvalidOperation
        value = self.cleaned_data.get(field_name)
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value)).quantize(Decimal('1'))
        except InvalidOperation:
            return Decimal('0')

    def clean_amount(self):
        return self._clean_integer_field('amount')

    def clean_tax(self):
        return self._clean_integer_field('tax')

    def clean_fee(self):
        return self._clean_integer_field('fee')

    def clean_allowance(self):
        return self._clean_integer_field('allowance')

    def clean_reporting_amount(self):
        return self._clean_integer_field('reporting_amount')

class ReportFilterForm(forms.Form):
    start_date = forms.DateField(
        label="開始日期",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'}),
        input_formats=['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']
    )
    end_date = forms.DateField(
        label="結束日期",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'}),
        input_formats=['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']
    )
    voucher_no = forms.CharField(
        label="傳票編號",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '例如: VOU-2024...', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'})
    )
    account_code_start = forms.CharField(
        label="起始科目代碼",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '例如: 1110', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'})
    )
    account_code_end = forms.CharField(
        label="結束科目代碼",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '例如: 4000', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'})
    )

class SubsidiaryLedgerFilterForm(forms.Form):
    start_date = forms.DateField(
        label="開始日期",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'}),
        input_formats=['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']
    )
    end_date = forms.DateField(
        label="結束日期",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'}),
        input_formats=['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']
    )
    account_code = forms.CharField(
        label="會計科目",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '必填，例如 1140 (應收帳款)', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'})
    )
    company_id = forms.CharField(
        label="對象/統編",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '可選，例如 12345678', 'class': 'w-full rounded border-[1.5px] border-stroke bg-transparent py-2 px-4 font-medium outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary'})
    )

class FixedAssetForm(forms.ModelForm):
    class Meta:
        model = FixedAsset
        fields = [
            'asset_no', 'name', 'purchase_date', 'cost', 'salvage_value', 
            'useful_life_months', 'accumulated_depreciation', 'status', 
            'depreciation_expense_account_code', 'accumulated_depreciation_account_code'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_class = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
        for field_name, field in self.fields.items():
            if 'class' in field.widget.attrs:
                field.widget.attrs['class'] += f' {default_class}'
            else:
                field.widget.attrs['class'] = default_class
        self.fields['purchase_date'].widget.input_type = 'date'
        self.fields['accumulated_depreciation'].widget.attrs['readonly'] = True
        self.fields['accumulated_depreciation'].widget.attrs['class'] += ' bg-slate-50 cursor-not-allowed'


class PreCollectionForm(forms.ModelForm):
    class Meta:
        model = PreCollection
        fields = ['date', 'company_name', 'unified_business_no', 'amount', 'method', 'transaction_no', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'unified_business_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'method': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'transaction_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50', 'readonly': 'readonly'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        }
