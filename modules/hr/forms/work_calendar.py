from django import forms
from ..models import WorkCalendar


class WorkCalendarForm(forms.ModelForm):
    class Meta:
        model = WorkCalendar
        fields = ['date', 'day_type', 'description']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'day_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例如：端午節、中秋節、補班日',
            }),
        }
