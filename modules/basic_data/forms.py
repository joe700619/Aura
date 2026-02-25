from django import forms
from .models import Contact, Customer, ServiceItem
from core.widgets import ModalSelectWidget

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'phone', 'mobile', 'fax', 'email', 'address', 'customer', 'tax_id', 'notes']
        widgets = {
            'customer': ModalSelectWidget(search_url='/basic-data/api/customers/search/', label_model=Customer),
            'notes': forms.Textarea(attrs={'rows': 3}),

        }

ContactInlineFormSet = forms.inlineformset_factory(
    Customer, Contact,
    fields=['name', 'phone', 'mobile', 'email', 'address', 'notes'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'placeholder': '姓名'}),
        'phone': forms.TextInput(attrs={'placeholder': '電話'}),
        'mobile': forms.TextInput(attrs={'placeholder': '手機'}),
        'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
        'address': forms.TextInput(attrs={'placeholder': '地址'}),
        'notes': forms.TextInput(attrs={'placeholder': '備註'}),
    }
)

class ServiceItemForm(forms.ModelForm):
    class Meta:
        model = ServiceItem
        fields = ['department', 'name', 'reference_fee', 'remark', 
                  'is_company_law_22_1', 'is_money_laundering_check', 'is_business_entity_change', 'is_shareholder_list_change']
        widgets = {
            'department': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入服務項目名稱'
            }),
            'reference_fee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right',
                'placeholder': '0'
            }),
            'remark': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 3,
                'placeholder': '備註'
            }),
            'is_company_law_22_1': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500',
            }),
            'is_money_laundering_check': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500',
            }),
            'is_business_entity_change': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500',
            }),
            'is_shareholder_list_change': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500',
            }),
        }
