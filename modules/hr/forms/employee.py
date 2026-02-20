from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Employee


class EmployeeForm(forms.ModelForm):
    """
    員工表單
    
    表單分為三個區塊：
    - 區塊一：基本資料
    - 區塊二：通訊方式
    - 區塊三：在職狀態
    """
    
    class Meta:
        model = Employee
        fields = [
            # 區塊一：基本資料
            'name',
            'gender',
            'id_number',
            'line_id',
            'extension',
            # 區塊二：通訊方式
            'phone',
            'address',
            'email',
            # 區塊三：在職狀態
            'employment_status',
            'hire_date',
            'resignation_date',
            'team',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入員工姓名'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：A123456789',
                'maxlength': '10'
            }),
            'line_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入 Line ID'
            }),
            'extension': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：101'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：02-12345678'
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入地址'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：employee@example.com'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            'resignation_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            'team': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
        }


