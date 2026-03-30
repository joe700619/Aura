from django import forms
from .models import DocumentReceipt
from modules.basic_data.models import Customer
from core.widgets import ModalSelectWidget

class DocumentReceiptForm(forms.ModelForm):
    class Meta:
        model = DocumentReceipt
        fields = ['customer', 'receipt_date', 'subject', 'category', 'status', 'remarks']
        widgets = {
            'customer': ModalSelectWidget(search_url='/basic-data/api/customers/search/', label_model=Customer),
            'receipt_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '輸入信件主旨',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 3,
                'placeholder': '輸入備註...',
            }),
        }

from .models import IrsAuditNotice, IrsAuditCommunication
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
User = get_user_model()

class IrsAuditNoticeForm(forms.ModelForm):
    class Meta:
        model = IrsAuditNotice
        fields = [
            'customer', 'tax_id', 'attributable_year', 'tax_category', 'subject', 'receipt_date', 'assigned_assistant', 'assistant_email',
            'reply_deadline', 'merge_annual_income_tax', 'status', 'remarks',
            'irs_phone', 'irs_contact', 'irs_email', 'irs_district'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Enforce required fields
        self.fields['assigned_assistant'].required = True
        self.fields['irs_contact'].required = True
        self.fields['irs_phone'].required = True
        self.fields['irs_district'].required = True
        
        # Applying standard Tailwind classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
                })
            elif not isinstance(field.widget, forms.CheckboxInput) and not isinstance(field.widget, ModalSelectWidget):
                field.widget.attrs.update({
                    'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
                })
        
        # Custom Widget Configurations
        self.fields['customer'].widget = ModalSelectWidget(
            search_url='/basic-data/api/customers/search/', 
            label_model=Customer
        )
        self.fields['customer'].widget.attrs.update({
             # Use alpine JS custom event or ID for fetching tax ID client-side
            'id': 'id_customer'
        })
        
        # Add id for tax_id to let JS easily target it
        self.fields['tax_id'].widget.attrs.update({'id': 'id_tax_id'})
        
        self.fields['receipt_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'})
        self.fields['reply_deadline'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'})
        
        self.fields['merge_annual_income_tax'].widget.attrs.update({
             'class': 'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500'
        })
        
        self.fields['assigned_assistant'].queryset = User.objects.filter(is_active=True)
        # Use simple select for assistant
        
        self.fields['remarks'].widget.attrs.update({'rows': 3})


IrsAuditCommunicationFormSet = inlineformset_factory(
    IrsAuditNotice,
    IrsAuditCommunication,
    fields=['comm_time', 'comm_content', 'reply_status'],
    extra=1,
    can_delete=True,
    widgets={
        'comm_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        'comm_content': forms.Textarea(attrs={'rows': 1, 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
        'reply_status': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
    }
)

from .models import DocumentDispatch, DocumentDispatchItem

class DocumentDispatchForm(forms.ModelForm):
    class Meta:
        model = DocumentDispatch
        fields = ['date', 'dispatch_method']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm'
            })
        self.fields['date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm'})

DocumentDispatchItemFormSet = inlineformset_factory(
    DocumentDispatch,
    DocumentDispatchItem,
    fields=['is_absorbed_by_customer', 'postage', 'customer', 'tax_id', 'address', 'contact_person', 'recipient', 'custom_message', 'is_notified'],
    extra=1,
    can_delete=True,
    widgets={
        'is_absorbed_by_customer': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
        'postage': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-right font-mono w-24'}),
        'customer': ModalSelectWidget(search_url='/basic-data/api/customers/search/', label_model=Customer),
        'tax_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm w-32'}),
        'address': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm w-64'}),
        'contact_person': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm w-24'}),
        'recipient': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm w-24'}),
        'custom_message': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm'}),
        'is_notified': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
    }
)

# ===== Seal Procurement =====
from .models import SealProcurement, SealProcurementItem
from django.utils.translation import gettext_lazy as _


class SealProcurementForm(forms.ModelForm):
    search_customer = forms.CharField(
        label=_('搜尋客戶'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/customers/search/progress/', button_label='帶入客戶')
    )

    search_contact = forms.CharField(
        label=_('搜尋聯絡人'),
        required=False,
        widget=ModalSelectWidget(search_url='/basic-data/api/contacts/search/progress/')
    )

    class Meta:
        model = SealProcurement
        fields = [
            'unified_business_no', 'company_name', 'line_id', 'room_id',
            'main_contact', 'mobile', 'phone', 'address',
            'transfer_to_advance', 'transfer_to_inventory', 'seal_cost_subtotal',
            'note',
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
            'transfer_to_advance': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
            'transfer_to_inventory': forms.Select(choices=[(False, '否'), (True, '是')], attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'seal_cost_subtotal': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-slate-500 text-sm', 'readonly': 'readonly'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }


class SealProcurementItemForm(forms.ModelForm):
    _ABSORBED_CHOICES = [('', '請選擇'), ('True', '是'), ('False', '否')]
    is_absorbed_by_customer = forms.ChoiceField(
        label=_('客戶吸收'),
        choices=_ABSORBED_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'w-full px-2 py-1.5 border border-slate-300 rounded-md text-sm', 'required': True})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert the bool from model instance to string so the select pre-selects correctly
        if self.instance and self.instance.pk is not None:
            self.initial['is_absorbed_by_customer'] = str(self.instance.is_absorbed_by_customer)

    def clean_is_absorbed_by_customer(self):
        val = self.cleaned_data.get('is_absorbed_by_customer')
        if val == '' or val is None:
            raise forms.ValidationError(_('此欄位為必填'))
        return val == 'True'

    class Meta:
        model = SealProcurementItem
        fields = ['is_absorbed_by_customer', 'movement_type', 'seal_type', 'quantity', 'name_or_address', 'unit_price', 'subtotal']
        widgets = {
            'movement_type': forms.Select(attrs={'class': 'w-full px-2 py-1.5 border border-slate-300 rounded-md text-sm', 'onchange': 'onMovementTypeChange(this)'}),
            'seal_type': forms.Select(attrs={'class': 'w-full px-2 py-1.5 border border-slate-300 rounded-md text-sm', 'onchange': 'updateSealPrice(this)'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-20 px-2 py-1.5 border border-slate-300 rounded-md text-sm text-center', 'min': '1', 'onchange': 'calculateSubtotal(this)'}),
            'name_or_address': forms.TextInput(attrs={'class': 'w-full px-2 py-1.5 border border-slate-300 rounded-md text-sm'}),
            'unit_price': forms.NumberInput(attrs={'class': 'w-24 px-2 py-1.5 border border-slate-300 rounded-md text-sm text-right font-mono', 'onchange': 'calculateSubtotal(this)'}),
            'subtotal': forms.NumberInput(attrs={'class': 'w-24 px-2 py-1.5 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
        }


SealProcurementItemFormSet = inlineformset_factory(
    SealProcurement,
    SealProcurementItem,
    form=SealProcurementItemForm,
    extra=0,
    can_delete=True,
)

# ===== System Bulletin Board =====
from .models.bulletin import SystemBulletin

class SystemBulletinCRUDForm(forms.ModelForm):
    class Meta:
        model = SystemBulletin
        fields = ['publish_date', 'subject', 'importance_level', 'content', 'status']
        widgets = {
            'publish_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm',
                'placeholder': '輸入公佈欄主題'
            }),
            'importance_level': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm'
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm',
                'rows': 5,
                'placeholder': '在此輸入公佈事項說明內容...'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm'
            }),
        }

# ===== Advance Payment =====
from .models.advance_payment import AdvancePayment, AdvancePaymentDetail

class AdvancePaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['total_amount'].required = False

    class Meta:
        model = AdvancePayment
        fields = [
            'advance_no', 'date', 'total_amount', 'description', 'note', 'is_posted'
        ]
        widgets = {
            'advance_no': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '系統自動產生或手動輸入'
            }),
            'date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50',
                'readonly': 'readonly' # Frontend calculates this
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 3,
                'placeholder': '請輸入摘要'
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 3,
                'placeholder': '其他備註說明'
            }),
            'is_posted': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500'
            }),
        }

class AdvancePaymentDetailForm(forms.ModelForm):
    class Meta:
        model = AdvancePaymentDetail
        fields = [
            'is_customer_absorbed', 'customer', 'unified_business_no', 
            'reason', 'amount', 'is_billed', 'payment_type'
        ]
        widgets = {
            'is_customer_absorbed': forms.Select(choices=[(True, 'Yes'), (False, 'No')], attrs={
                'class': 'w-full px-2 py-1.5 border border-slate-300 rounded text-sm focus:ring-blue-500 focus:border-blue-500 is-absorbed-select'
            }),
            'customer': ModalSelectWidget(
                search_url='/basic-data/api/customers/search/', 
                label_model=Customer
            ),
            'unified_business_no': forms.TextInput(attrs={
                'class': 'w-full px-2 py-1.5 border border-slate-300 rounded text-sm focus:ring-blue-500 focus:border-blue-500 ubn-input',
            }),
            'reason': forms.TextInput(attrs={
                'class': 'w-full px-2 py-1.5 border border-slate-300 rounded text-sm focus:ring-blue-500 focus:border-blue-500 reason-input'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-2 py-1.5 border border-slate-300 rounded text-sm focus:ring-blue-500 focus:border-blue-500 amount-input text-right',
                'step': '1'
            }),
            'is_billed': forms.Select(choices=[(True, 'Yes'), (False, 'No')], attrs={
                'class': 'w-full px-2 py-1.5 border border-slate-300 rounded text-sm focus:ring-blue-500 focus:border-blue-500'
            }),
            'payment_type': forms.Select(attrs={
                'class': 'w-full px-2 py-1.5 border border-slate-300 rounded text-sm focus:ring-blue-500 focus:border-blue-500 payment-type-select'
            }),
        }

AdvancePaymentDetailFormSet = inlineformset_factory(
    AdvancePayment,
    AdvancePaymentDetail,
    form=AdvancePaymentDetailForm,
    extra=1,
    can_delete=True,
    fields=['is_customer_absorbed', 'customer', 'unified_business_no', 'reason', 'amount', 'is_billed', 'payment_type']
)
