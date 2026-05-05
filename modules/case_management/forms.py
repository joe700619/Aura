from django import forms
from django.contrib.auth import get_user_model

from modules.bookkeeping.models import BookkeepingClient

from .models import Case, CaseReply, CaseTask, CaseAttachment


User = get_user_model()


class CaseInternalCreateForm(forms.ModelForm):
    """內部建立案件表單

    兩段式設計：
    - target_type='client' → 選擇既有 BookkeepingClient，自動帶入聯絡資訊
    - target_type='other'  → 手動輸入外部聯絡人（一次性諮詢、潛在客戶等）
    """

    TARGET_CLIENT = 'client'
    TARGET_OTHER = 'other'
    TARGET_CHOICES = [
        (TARGET_CLIENT, '既有記帳客戶'),
        (TARGET_OTHER, '其他外部聯絡人'),
    ]

    target_type = forms.ChoiceField(
        choices=TARGET_CHOICES, initial=TARGET_CLIENT,
        widget=forms.HiddenInput(),
        label='案件對象',
    )
    bookkeeping_client = forms.ModelChoiceField(
        queryset=BookkeepingClient.objects.filter(is_deleted=False),
        required=False,
        widget=forms.HiddenInput(),
        label='記帳客戶',
    )

    class Meta:
        model = Case
        fields = [
            'title', 'summary', 'category', 'priority', 'owner',
            'external_contact_name', 'external_contact_email', 'external_contact_phone',
            'needs_followup', 'next_followup_date', 'expected_completion_date',
        ]
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 3}),
            'next_followup_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 限制負責會計師只能是內部使用者；用 modal 搜尋取代下拉
        self.fields['owner'].queryset = User.objects.filter(
            is_active=True
        ).exclude(role='EXTERNAL')
        self.fields['owner'].widget = forms.HiddenInput()
        # 外部聯絡人欄位在「既有客戶」模式自動帶入，所以這裡都設為非必填
        for fn in ('external_contact_name', 'external_contact_email', 'external_contact_phone'):
            self.fields[fn].required = False

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get('target_type')
        if target == self.TARGET_CLIENT:
            if not cleaned.get('bookkeeping_client'):
                self.add_error('bookkeeping_client', '請選擇記帳客戶')
        else:
            if not cleaned.get('external_contact_name'):
                self.add_error('external_contact_name', '請填寫外部聯絡人姓名')
        return cleaned


class CaseClientCreateForm(forms.ModelForm):
    """客戶端發起案件表單"""
    class Meta:
        model = Case
        fields = ['title', 'summary', 'category', 'priority', 'expected_completion_date']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 6}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date'}),
        }


class CaseReplyForm(forms.ModelForm):
    class Meta:
        model = CaseReply
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'rows': 3})}


class CaseTaskForm(forms.ModelForm):
    class Meta:
        model = CaseTask
        fields = ['title', 'assignee_type', 'due_date']
        widgets = {'due_date': forms.DateInput(attrs={'type': 'date'})}


class CaseAttachmentForm(forms.ModelForm):
    class Meta:
        model = CaseAttachment
        fields = ['file']
