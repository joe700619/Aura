from django import forms

from modules.bookkeeping.models import ServiceRemuneration, ServiceRemunerationTaxRate

_INPUT = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
_DATE_INPUT = _INPUT
_TEXTAREA = _INPUT
_SELECT = _INPUT


class ServiceRemunerationForm(forms.ModelForm):
    class Meta:
        model = ServiceRemuneration
        fields = [
            # 基本資料
            'recipient_name', 'recipient_email', 'nationality',
            'id_number', 'has_nhi', 'residence_address', 'phone', 'joined_union',
            # 勞報資料
            'income_category', 'professional_category',
            'amount', 'service_content',
            'service_start_date', 'service_end_date', 'filing_date', 'company_name',
            # 支付資料
            'payment_method', 'bank_code', 'branch_name', 'bank_account', 'account_holder',
            # 附件
            'id_front_image', 'id_back_image',
        ]
        widgets = {
            'recipient_name':       forms.TextInput(attrs={'class': _INPUT, 'placeholder': '所得人姓名'}),
            'recipient_email':      forms.EmailInput(attrs={'class': _INPUT, 'placeholder': 'name@example.com'}),
            'nationality':          forms.Select(attrs={'class': _SELECT}),
            'id_number':            forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'A123456789'}),
            'residence_address':    forms.TextInput(attrs={'class': _INPUT}),
            'phone':                forms.TextInput(attrs={'class': _INPUT}),
            'income_category':      forms.Select(attrs={'class': _SELECT}),
            'professional_category':forms.Select(attrs={'class': _SELECT}),
            'amount':               forms.NumberInput(attrs={'class': _INPUT, 'min': 0}),
            'service_content':      forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'service_start_date':   forms.DateInput(attrs={'class': _DATE_INPUT, 'type': 'date'}),
            'service_end_date':     forms.DateInput(attrs={'class': _DATE_INPUT, 'type': 'date'}),
            'filing_date':          forms.DateInput(attrs={'class': _DATE_INPUT, 'type': 'date'}),
            'company_name':         forms.TextInput(attrs={'class': _INPUT}),
            'payment_method':       forms.Select(attrs={'class': _SELECT}),
            'bank_code':            forms.TextInput(attrs={'class': _INPUT, 'placeholder': '例：004 台灣銀行'}),
            'branch_name':          forms.TextInput(attrs={'class': _INPUT}),
            'bank_account':         forms.TextInput(attrs={'class': _INPUT}),
            'account_holder':       forms.TextInput(attrs={'class': _INPUT}),
        }


class TaxRateForm(forms.ModelForm):
    class Meta:
        model = ServiceRemunerationTaxRate
        fields = ['code', 'label', 'withholding_rate', 'expense_rate', 'description', 'is_active', 'sort_order']
        widgets = {
            'code':              forms.TextInput(attrs={'class': _INPUT}),
            'label':             forms.TextInput(attrs={'class': _INPUT}),
            'withholding_rate':  forms.NumberInput(attrs={'class': _INPUT, 'step': '0.01'}),
            'expense_rate':      forms.NumberInput(attrs={'class': _INPUT, 'step': '0.01'}),
            'description':       forms.TextInput(attrs={'class': _INPUT}),
            'sort_order':        forms.NumberInput(attrs={'class': _INPUT}),
        }
