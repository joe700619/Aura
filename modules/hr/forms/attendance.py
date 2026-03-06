from django import forms
from ..models import AttendanceRecord


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['employee', 'date', 'clock_in', 'clock_out', 'source', 'makeup_reason', 'note']
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'clock_in': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'clock_out': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'source': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'makeup_reason': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 2,
                'placeholder': '補卡時必須填寫事由',
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 2,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        makeup_reason = cleaned_data.get('makeup_reason')

        if source == 'makeup' and not makeup_reason:
            self.add_error('makeup_reason', '補卡時必須填寫事由。')

        return cleaned_data


class ClockInOutForm(forms.Form):
    """員工自助打卡表單（只需選上班/下班）"""
    CLOCK_CHOICES = [
        ('in', '上班打卡'),
        ('out', '下班打卡'),
    ]
    clock_type = forms.ChoiceField(
        choices=CLOCK_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'mr-2'}),
        label='打卡類型',
    )
