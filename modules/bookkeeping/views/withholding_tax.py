import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import UpdateView

from ..models.income_tax import (
    WithholdingTax, WithholdingDetail, WithholdingMonthlyBreakdown,
)

# 月分明細的 period 清單（固定順序）
PERIOD_CHOICES = [c[0] for c in WithholdingMonthlyBreakdown.Period.choices]
PERIOD_LABELS = {c[0]: c[1] for c in WithholdingMonthlyBreakdown.Period.choices}


class WithholdingTaxDetailView(LoginRequiredMixin, UpdateView):
    model = WithholdingTax
    fields = ['salary_payment_method', 'interest_income', 'notes']
    template_name = 'bookkeeping/income_tax/withholding_tax_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            WithholdingTax,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_success_url(self):
        return reverse('bookkeeping:withholding_tax_detail', kwargs={
            'client_pk': self.kwargs['client_pk'],
            'pk': self.object.pk,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wt = self.object
        client = wt.year_record.client
        context['client'] = client
        context['withholding'] = wt
        context['year_obj'] = wt.year_record
        context['setting'] = getattr(client, 'income_tax_setting', None)

        # Build details JSON for Alpine.js
        details_json = []
        for d in wt.details.all().prefetch_related('monthly_breakdowns'):
            # Build monthly breakdown map
            breakdowns = {}
            for mb in d.monthly_breakdowns.all():
                breakdowns[mb.period] = {
                    'salary': float(mb.salary),
                    'retirement_contribution': float(mb.retirement_contribution),
                    'tax': float(mb.tax),
                    'meal_allowance': float(mb.meal_allowance),
                    'overtime_pay': float(mb.overtime_pay),
                }
            # Fill in missing periods with zeros
            monthly = []
            for p in PERIOD_CHOICES:
                row = breakdowns.get(p, {
                    'salary': 0, 'retirement_contribution': 0,
                    'tax': 0, 'meal_allowance': 0, 'overtime_pay': 0,
                })
                row['period'] = p
                row['label'] = PERIOD_LABELS[p]
                monthly.append(row)

            details_json.append({
                'id': str(d.pk),
                'certificate_no': d.certificate_no,
                'recipient_name': d.recipient_name,
                'id_number': d.id_number,
                'address': d.address,
                'income_category': d.income_category,
                'category_name': d.category_name,
                'lease_no': d.lease_no,
                'total_amount': float(d.total_amount),
                'tax_withheld': float(d.tax_withheld),
                'monthly': monthly,
            })

        context['details_json'] = json.dumps(details_json, ensure_ascii=False)
        context['period_choices'] = json.dumps(
            [{'value': p, 'label': PERIOD_LABELS[p]} for p in PERIOD_CHOICES],
            ensure_ascii=False,
        )
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.required = False
        return form

    def form_valid(self, form):
        wt = form.save(commit=False)

        # Parse POST values
        wt.salary_payment_method = self.request.POST.get('salary_payment_method', '') or None
        val = self.request.POST.get('interest_income', '0')
        try:
            wt.interest_income = int(val) if val else 0
        except (ValueError, TypeError):
            wt.interest_income = 0

        # Filing status fields
        wt.payment_method = self.request.POST.get('payment_method', wt.payment_method)
        wt.filing_status = self.request.POST.get('filing_status', wt.filing_status)
        wt.is_filed = self.request.POST.get('is_filed') == 'on'
        wt.notes = self.request.POST.get('notes', '')

        wt.save()

        # Save detail rows from POST
        self._save_details(wt)

        messages.success(self.request, '扣繳申報資料已儲存。')
        return super().form_valid(form)

    def _save_details(self, wt):
        """Save inline detail rows + monthly breakdowns from POST data."""
        existing_ids = set(wt.details.values_list('pk', flat=True))
        posted_ids = set()
        i = 0
        while True:
            name = self.request.POST.get(f'dt_{i}_recipient_name')
            if name is None:
                break

            dt_id = self.request.POST.get(f'dt_{i}_id', '')
            if dt_id:
                try:
                    detail = WithholdingDetail.objects.get(pk=dt_id, withholding_tax=wt)
                    posted_ids.add(detail.pk)
                except WithholdingDetail.DoesNotExist:
                    detail = WithholdingDetail(withholding_tax=wt)
            else:
                detail = WithholdingDetail(withholding_tax=wt)

            detail.certificate_no = self.request.POST.get(f'dt_{i}_certificate_no', '')
            detail.recipient_name = name
            detail.id_number = self.request.POST.get(f'dt_{i}_id_number', '')
            detail.address = self.request.POST.get(f'dt_{i}_address', '')
            detail.income_category = self.request.POST.get(f'dt_{i}_income_category', 'salary')
            detail.category_name = self.request.POST.get(f'dt_{i}_category_name', '')
            detail.lease_no = self.request.POST.get(f'dt_{i}_lease_no', '')
            detail.total_amount = int(self.request.POST.get(f'dt_{i}_total_amount', 0) or 0)
            detail.tax_withheld = int(self.request.POST.get(f'dt_{i}_tax_withheld', 0) or 0)
            detail.save()
            if detail.pk:
                posted_ids.add(detail.pk)

            # Save monthly breakdowns
            self._save_monthly(detail, i)
            i += 1

        # Delete removed rows
        to_delete = existing_ids - posted_ids
        if to_delete:
            WithholdingDetail.objects.filter(pk__in=to_delete).delete()

    def _save_monthly(self, detail, row_idx):
        """Save monthly breakdown for a detail row."""
        # Delete existing and recreate
        detail.monthly_breakdowns.all().delete()
        breakdowns = []
        for p in PERIOD_CHOICES:
            salary = int(self.request.POST.get(f'dt_{row_idx}_mb_{p}_salary', 0) or 0)
            retirement = int(self.request.POST.get(f'dt_{row_idx}_mb_{p}_retirement_contribution', 0) or 0)
            tax = int(self.request.POST.get(f'dt_{row_idx}_mb_{p}_tax', 0) or 0)
            meal = int(self.request.POST.get(f'dt_{row_idx}_mb_{p}_meal_allowance', 0) or 0)
            overtime = int(self.request.POST.get(f'dt_{row_idx}_mb_{p}_overtime_pay', 0) or 0)
            # Only save if at least one value is non-zero
            if any([salary, retirement, tax, meal, overtime]):
                breakdowns.append(WithholdingMonthlyBreakdown(
                    detail=detail,
                    period=p,
                    salary=salary,
                    retirement_contribution=retirement,
                    tax=tax,
                    meal_allowance=meal,
                    overtime_pay=overtime,
                ))
        if breakdowns:
            WithholdingMonthlyBreakdown.objects.bulk_create(breakdowns)
