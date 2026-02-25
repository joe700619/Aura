from django import forms
from django.forms import inlineformset_factory
from core.widgets import ModalSelectWidget
from .models import Account, Voucher, VoucherDetail, Receivable, ReceivableFeeApportion, PaymentRecord, Collection

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
    voucher_no = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm bg-slate-50', 'readonly': 'readonly', 'placeholder': '(存檔後由系統自動產生)'}))
    creator_name = forms.CharField(label="編輯者", required=False, widget=forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm bg-slate-50', 'readonly': 'readonly'}))

    class Meta:
        model = Voucher
        fields = ['date', 'voucher_no', 'description', 'status', 'source']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'status': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'source': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm bg-slate-50'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source'].disabled = True
        
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
            'account': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm select2 account-select'}),
            'debit': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right debit-input', 'step': '0.01'}),
            'credit': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right credit-input', 'step': '0.01'}),
            'company_id': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'department': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'project': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'remark': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'DELETE': forms.CheckboxInput(attrs={'class': 'delete-checkbox hidden'}),
        }

VoucherDetailFormSet = inlineformset_factory(
    Voucher, 
    VoucherDetail, 
    form=VoucherDetailForm,
    extra=5,
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
            'receivable_no', 'company_name', 'unified_business_no', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address', 'email',
            'assistant', 'assistant_email', 'is_posted', 'remarks',
            'quotation_data', 'cost_sharing_data'
        ]
        widgets = {
            'receivable_no': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm', 'placeholder': '應收帳款編號'}),
            'company_name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'unified_business_no': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'line_id': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'room_id': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'main_contact': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'mobile': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'address': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'assistant': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'assistant_email': forms.EmailInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'is_posted': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
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
            'is_correction_needed', 'reporting_amount', 'is_posted', 'remarks'
        ]
        widgets = {
            'receivable': forms.HiddenInput(),
            'collection_no': forms.TextInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm bg-slate-50', 'readonly': 'readonly', 'placeholder': '(自動產生)'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'method': forms.Select(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right calc-input', 'step': '0.01'}),
            'tax': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right calc-input', 'step': '0.01'}),
            'fee': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right calc-input', 'step': '0.01'}),
            'allowance': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right calc-input', 'step': '0.01'}),
            'total': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right bg-slate-50', 'readonly': 'readonly', 'step': '0.01'}),
            'is_correction_needed': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
            'reporting_amount': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm text-right', 'step': '0.01'}),
            'is_posted': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
        }

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
