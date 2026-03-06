from django import forms
from ..models import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['code', 'name', 'is_paid', 'max_hours_per_year', 'requires_doc', 'description', 'sort_order']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例如：annual, sick, personal',
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例如：特休、病假、事假',
            }),
            'is_paid': forms.Select(choices=[(True, '是'), (False, '否')], attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'max_hours_per_year': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'step': '0.5',
                'placeholder': '留空代表無上限',
            }),
            'requires_doc': forms.Select(choices=[(False, '否'), (True, '是')], attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 2,
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
        }


class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = ['employee', 'leave_type', 'year', 'entitled_hours', 'used_hours', 'manually_granted']
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'leave_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'entitled_hours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'step': '0.5',
            }),
            'used_hours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm bg-slate-50',
                'step': '0.5',
                'readonly': 'readonly',
            }),
            'manually_granted': forms.Select(choices=[(False, '否'), (True, '是')], attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
        }


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_datetime', 'end_datetime', 'total_hours', 'reason', 'attachment', 'note']
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'leave_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
            'total_hours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'step': '0.5',
                'min': '0.5',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 2,
                'placeholder': '請填寫請假事由',
            }),
            'attachment': forms.ClearableFileInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-sm file:bg-blue-50 file:text-blue-700',
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'rows': 2,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')
        total_hours = cleaned_data.get('total_hours')
        start_datetime = cleaned_data.get('start_datetime')

        if employee and leave_type and total_hours and start_datetime:
            # Check balance
            balance = LeaveBalance.objects.filter(
                employee=employee,
                leave_type=leave_type,
                year=start_datetime.year,
            ).first()

            if balance:
                if balance.remaining_hours < total_hours:
                    self.add_error(
                        'total_hours',
                        f'餘額不足！{leave_type.name} 剩餘 {balance.remaining_hours} 小時，'
                        f'您申請了 {total_hours} 小時。'
                    )
            else:
                # No balance record - check if leave type has max_hours
                if leave_type.max_hours_per_year is not None:
                    self.add_error(
                        'leave_type',
                        f'您在 {start_datetime.year} 年度尚無「{leave_type.name}」的假期餘額，請聯繫管理員。'
                    )

        return cleaned_data
