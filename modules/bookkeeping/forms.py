from django import forms
from modules.basic_data.models import Customer
from core.widgets import ModalSelectWidget
from .models import BookkeepingClient


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
            'customer', 'tax_id', 'tax_registration_no', 'name', 'line_id', 'room_id',
            'contact_person', 'phone', 'mobile', 'email',
            'correspondence_address', 'registered_address',
            'acceptance_status', 'billing_status', 'service_type',
            'group_assistant', 'bookkeeping_assistant',
            'has_group_invoice',
            'send_invoice_method', 'send_merged_client_name',
            'receive_invoice_method', 'receive_merged_client_name',
            'last_convenience_bag_date', 'last_convenience_bag_qty',
            'notes', 'cost_sharing_data', 'client_source', 'contact_date', 'transfer_checklist',
            'business_password', 'national_tax_password', 'e_invoice_account', 'e_invoice_password',
        ]
        widgets = {
            'customer': ModalSelectWidget(
                search_url='/basic-data/api/customers/search/',
                label_model=Customer,
                button_label='請選擇客戶...',
            ),
        }
