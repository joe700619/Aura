from django import forms
from ..models import LeaveType, LeaveBalance, LeaveRequest
from ..services.leave_duration import calculate_leave_hours


class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['code', 'name', 'pay_rate', 'max_hours_per_year', 'requires_doc', 'description', 'sort_order']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例如：annual, sick, personal',
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例如：特休、病假、事假',
            }),
            'pay_rate': forms.Select(choices=[('1.00', '全薪'), ('0.50', '半薪'), ('0.00', '無薪')], attrs={
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
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-slate-50',
                'step': '0.5',
                'min': '0.5',
                'readonly': 'readonly',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 時數由後端依上下班時段自動計算，前端僅作預覽，故表單層不必填
        self.fields['total_hours'].required = False

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')

        # 後端權威重算時數：不信任前端送來的 total_hours，
        # 依固定上班時段（扣午休）逐工作日計算（跳過週末/國定假日）
        if start_datetime and end_datetime:
            if end_datetime <= start_datetime:
                self.add_error('end_datetime', '結束時間必須晚於開始時間。')
            else:
                total_hours = calculate_leave_hours(start_datetime, end_datetime)
                cleaned_data['total_hours'] = total_hours
                if total_hours <= 0:
                    self.add_error(
                        'start_datetime',
                        '此區間不含任何工作時段（可能整段落在午休、下班時間或假日），請重新選擇。'
                    )
        total_hours = cleaned_data.get('total_hours')

        if employee and leave_type and total_hours and start_datetime:
            # Check balance
            # 特休為週年制，餘額期間不等於曆年，必須用區間判斷（比照 LeaveRequest.cancel()）
            start_date = start_datetime.date()
            balance = LeaveBalance.objects.filter(
                employee=employee,
                leave_type=leave_type,
                period_start__lte=start_date,
                period_end__gt=start_date,
                is_deleted=False,
            ).first()

            if not balance:
                # Fallback：舊資料可能未填 period 區間
                balance = LeaveBalance.objects.filter(
                    employee=employee,
                    leave_type=leave_type,
                    year=start_datetime.year,
                    is_deleted=False,
                ).first()

            if balance:
                available = balance.remaining_hours
                # 編輯既有假單時，這張單原本已扣抵的時數仍記在 used_hours 裡，
                # 若扣在「同一筆餘額」上，要先加回來再驗證，否則改小時數會被自己舊額度誤擋
                if self.instance.pk and self.instance.status in ('pending', 'approved'):
                    old_balance = self.instance._find_balance()
                    if old_balance and old_balance.pk == balance.pk:
                        available += self.instance.total_hours

                if available < total_hours:
                    self.add_error(
                        'total_hours',
                        f'餘額不足！{leave_type.name} 剩餘 {available} 小時，'
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
