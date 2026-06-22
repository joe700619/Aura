from django import forms
from django.conf import settings
from modules.basic_data.models import Customer
from core.widgets import ModalSelectWidget
from .models import BookkeepingClient, EngagementLetter


# 表單欄位統一 Tailwind 樣式（form_view 無全域 input 樣式，各表單自套）。
_INPUT_CLS = ('w-full border border-slate-300 rounded-md px-3 py-2 text-sm '
              'focus:ring-2 focus:ring-blue-500 focus:border-blue-500')


class BookkeepingClientForm(forms.ModelForm):

    def clean_tax_id(self):
        tax_id = self.cleaned_data.get('tax_id')
        if tax_id:
            qs = BookkeepingClient.objects.filter(tax_id=tax_id, is_deleted=False)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('此統一編號已有其他記帳客戶使用。')
        return tax_id

    class Meta:
        model = BookkeepingClient
        fields = [
            'customer', 'tax_id', 'tax_registration_no', 'tax_authority_code', 'name', 'line_id', 'room_id',
            'contact_person', 'phone', 'mobile', 'email',
            'correspondence_address', 'registered_address',
            'acceptance_status', 'billing_status', 'service_type',
            'group_assistant', 'bookkeeping_assistant',
            'has_group_invoice',
            'send_invoice_method', 'send_merged_client_name',
            'receive_invoice_method', 'receive_merged_client_name',
            'last_convenience_bag_date', 'last_convenience_bag_qty',
            'notes', 'cost_sharing_data', 'client_source', 'contact_date', 'transfer_checklist',
            'national_tax_password', 'e_invoice_account', 'e_invoice_password',
            'notification_method', 'payment_method',
            'company_act_22_1_filing',
        ]
        widgets = {
            'customer': ModalSelectWidget(
                search_url='/basic-data/api/customers/search/',
                label_model=Customer,
                button_label='請選擇客戶...',
            ),
        }


class EngagementLetterForm(forms.ModelForm):
    """記帳委任書草稿表單。template_version 由 view 自動帶 active 範本，不在此選。"""

    class Meta:
        model = EngagementLetter
        fields = [
            'inquiry', 'progress_no',
            'company_name', 'tax_id', 'contact_name', 'contact_email',
            'contact_phone', 'client_source',
            'engagement_start_date', 'pricing_type', 'firm_name',
            'service_fee', 'ledger_fee', 'billing_cycle', 'fee_note',
        ]
        widgets = {
            'engagement_start_date': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fee_note': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 新建時預帶基礎方案月費
        if not self.instance.pk and not self.initial.get('service_fee'):
            self.fields['service_fee'].initial = getattr(
                settings, 'BOOKKEEPING_BASE_MONTHLY_FEE', 2000)
        self.fields['inquiry'].required = False
        for name, field in self.fields.items():
            base = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (base + ' ' + _INPUT_CLS).strip()
