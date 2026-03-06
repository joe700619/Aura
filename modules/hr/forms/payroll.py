from django import forms
from ..models import SalaryStructure, OvertimeRecord, PayrollRecord, InsuranceBracket, AdvancePayment


class SalaryStructureForm(forms.ModelForm):
    class Meta:
        model = SalaryStructure
        fields = [
            'employee', 'base_salary', 'meal_allowance', 'transport_allowance',
            'other_allowance', 'labor_insurance', 'health_insurance',
            'labor_insurance_employer', 'health_insurance_employer',
            'pension_employer', 'occupational_hazard_employer', 'wage_arrears_employer',
            'effective_date', 'is_current', 'note',
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'base_salary': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'meal_allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'transport_allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'other_allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'labor_insurance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'health_insurance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'labor_insurance_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'health_insurance_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'pension_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'occupational_hazard_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'wage_arrears_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'effective_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'is_current': forms.Select(choices=[(True, '是'), (False, '否')], attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 2}),
        }


class InsuranceBracketForm(forms.ModelForm):
    class Meta:
        model = InsuranceBracket
        fields = [
            'level_name', 'insured_salary',
            'labor_employee', 'health_employee',
            'labor_employer', 'health_employer', 'pension_employer',
            'occupational_hazard', 'wage_arrears'
        ]
        widgets = {
            'level_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'insured_salary': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'labor_employee': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'health_employee': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'labor_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'health_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'pension_employer': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'occupational_hazard': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'wage_arrears': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
        }


class OvertimeRecordForm(forms.ModelForm):
    class Meta:
        model = OvertimeRecord
        fields = ['employee', 'date', 'hours', 'rate', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'hours': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'step': '0.5', 'min': '0.5'}),
            'rate': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'reason': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 2}),
        }


class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            'employee', 'year_month',
            'work_days_required', 'work_days_actual',
            'base_salary', 'meal_allowance', 'transport_allowance', 'other_allowance',
            'overtime_pay', 'bonus_pay', 'leave_settlement_pay', 'advance_payment_deduction', 'gross_salary',
            'labor_insurance', 'health_insurance', 'leave_deduction', 'late_deduction', 'missing_punch_deduction', 'other_deduction',
            'net_salary', 'is_finalized', 'note',
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'year_month': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'placeholder': '2026-03'}),
            'work_days_required': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'work_days_actual': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'base_salary': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'meal_allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'transport_allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'other_allowance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'overtime_pay': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'bonus_pay': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-right font-mono font-bold text-blue-600'}),
            'leave_settlement_pay': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono text-purple-600 font-bold', 'readonly': 'readonly'}),
            'advance_payment_deduction': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono text-green-600 font-bold', 'readonly': 'readonly'}),
            'gross_salary': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-blue-50 text-sm text-right font-mono font-bold', 'readonly': 'readonly'}),
            'labor_insurance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'health_insurance': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'leave_deduction': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-50 text-sm text-right font-mono', 'readonly': 'readonly'}),
            'late_deduction': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-right font-mono text-orange-600 font-bold'}),
            'missing_punch_deduction': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-right font-mono text-orange-600 font-bold'}),
            'other_deduction': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-right font-mono'}),
            'net_salary': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md bg-green-50 text-sm text-right font-mono font-bold', 'readonly': 'readonly'}),
            'is_finalized': forms.Select(choices=[(False, '否'), (True, '是')], attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'note': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 2}),
        }

class AdvancePaymentForm(forms.ModelForm):
    class Meta:
        model = AdvancePayment
        fields = ['employee', 'date_applied', 'amount', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'date_applied': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm text-right font-mono'}),
            'reason': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm', 'rows': 3}),
        }

