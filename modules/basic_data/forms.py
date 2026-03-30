from django import forms
from .models import Contact, Customer, ServiceItem
from core.widgets import ModalSelectWidget

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'tax_id', 'name', 'email', 'phone', 'mobile', 'source', 'line_id', 'room_id',
            'registered_zip', 'registered_address', 'correspondence_zip', 'correspondence_address',
            'bank_account_last5', 'labor_ins_code', 'health_ins_code', 'contact_person', 'notes'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tax_id'].required = True
        default_class = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += f' {default_class}'
                else:
                    field.widget.attrs['class'] = default_class
                
        # 特定的 placeholders & attributes
        self.fields['tax_id'].widget.attrs.update({'placeholder': '8位數字'})
        self.fields['name'].widget.attrs.update({'placeholder': '請輸入客戶公司名稱'})
        self.fields['bank_account_last5'].widget.attrs.update({'placeholder': '12345'})
        self.fields['notes'].widget.attrs.update({'rows': 3})

    def clean_tax_id(self):
        tax_id = self.cleaned_data.get('tax_id')
        if not tax_id:
            raise forms.ValidationError("統一編號為必填欄位")
            
        qs = Customer.objects.filter(tax_id=tax_id)
        if hasattr(Customer, 'is_deleted'):
            qs = qs.filter(is_deleted=False)
            
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise forms.ValidationError("此統一編號已經存在（且未被刪除）")
            
        return tax_id

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'phone', 'mobile', 'fax', 'email', 'address', 'customer', 'tax_id', 'notes']
        widgets = {
            'customer': ModalSelectWidget(search_url='/basic-data/api/customers/search/', label_model=Customer),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_class = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect, ModalSelectWidget)):
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += f' {default_class}'
                else:
                    field.widget.attrs['class'] = default_class

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

