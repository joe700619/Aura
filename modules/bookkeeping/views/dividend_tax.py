import json
from core.mixins import BusinessRequiredMixin
import math
from datetime import date
from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import UpdateView

from ..models.income_tax import DividendTax, ShareholderDividend


class DividendTaxDetailView(BusinessRequiredMixin, UpdateView):
    model = DividendTax
    fields = [
        'last_year_profit', 'accumulated_loss', 'distributable_amount',
        'distributed_amount', 'undistributed_surtax', 'notes',
    ]
    template_name = 'bookkeeping/income_tax/dividend_tax_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            DividendTax,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_success_url(self):
        return reverse('bookkeeping:dividend_tax_detail', kwargs={
            'client_pk': self.kwargs['client_pk'],
            'pk': self.object.pk,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dividend = self.object
        client = dividend.year_record.client
        context['client'] = client
        context['dividend'] = dividend
        context['year_obj'] = dividend.year_record
        context['setting'] = getattr(client, 'income_tax_setting', None)
        context['shareholders'] = dividend.shareholders.all()

        # JSON for Alpine.js table
        shareholders_json = []
        for s in context['shareholders']:
            shareholders_json.append({
                'id': str(s.pk),
                'name': s.shareholder_name,
                'id_number': s.id_number,
                'stock_type': s.stock_type,
                'share_count': s.share_count,
                'face_value': float(s.face_value),
                'share_amount': float(s.share_amount),
                'share_ratio': float(s.share_ratio),
                'dividend_amount': float(s.dividend_amount),
                'personal_tax_rate': float(s.personal_tax_rate),
                'tax_amount': float(s.tax_amount),
                'imputation_credit': float(s.imputation_credit),
                'insurance_base': float(s.insurance_base),
                'supplement_premium_rate': float(s.supplement_premium_rate),
                'supplement_premium': float(s.supplement_premium),
                'total_tax_premium': float(s.total_tax_premium),
            })
        context['shareholders_json'] = json.dumps(shareholders_json, ensure_ascii=False)

        # Default import date = year/12/1
        if dividend.import_date:
            context['default_import_date'] = dividend.import_date.strftime('%Y-%m-%d')
        else:
            year = dividend.year_record.year
            # Convert ROC year to AD
            ad_year = year + 1911
            context['default_import_date'] = f'{ad_year}-12-01'

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.required = False
        return form

    def form_valid(self, form):
        dividend = form.save(commit=False)

        # Parse POST values
        for field_name in ['last_year_profit', 'accumulated_loss', 'distributable_amount',
                           'distributed_amount', 'undistributed_surtax']:
            val = self.request.POST.get(field_name, '0')
            try:
                setattr(dividend, field_name, int(val) if val else 0)
            except (ValueError, TypeError):
                setattr(dividend, field_name, 0)

        # Filing status fields from IncomeTaxItemBase
        dividend.payment_method = self.request.POST.get('payment_method', dividend.payment_method)
        dividend.filing_status = self.request.POST.get('filing_status', dividend.filing_status)
        dividend.is_filed = self.request.POST.get('is_filed') == 'on'
        dividend.notes = self.request.POST.get('notes', '')

        # Save shareholder data from POST
        self._save_shareholders(dividend)

        dividend.save()
        messages.success(self.request, '股利申報資料已儲存。')
        return super().form_valid(form)

    def _save_shareholders(self, dividend):
        """Save inline shareholder rows from POST data."""
        existing_ids = set(
            dividend.shareholders.values_list('pk', flat=True)
        )
        posted_ids = set()
        i = 0
        while True:
            name = self.request.POST.get(f'sh_{i}_name')
            if name is None:
                break
            sh_id = self.request.POST.get(f'sh_{i}_id', '')
            if sh_id:
                try:
                    sh = ShareholderDividend.objects.get(pk=sh_id, dividend_tax=dividend)
                    posted_ids.add(sh.pk)
                except ShareholderDividend.DoesNotExist:
                    sh = ShareholderDividend(dividend_tax=dividend)
            else:
                sh = ShareholderDividend(dividend_tax=dividend)

            sh.shareholder_name = name
            sh.id_number = self.request.POST.get(f'sh_{i}_id_number', '')
            sh.stock_type = self.request.POST.get(f'sh_{i}_stock_type', 'COMMON')
            sh.share_count = int(self.request.POST.get(f'sh_{i}_share_count', 0) or 0)
            sh.face_value = int(self.request.POST.get(f'sh_{i}_face_value', 10) or 10)
            sh.share_amount = int(self.request.POST.get(f'sh_{i}_share_amount', 0) or 0)
            sh.share_ratio = float(self.request.POST.get(f'sh_{i}_share_ratio', 0) or 0)
            sh.dividend_amount = int(self.request.POST.get(f'sh_{i}_dividend_amount', 0) or 0)
            sh.personal_tax_rate = float(self.request.POST.get(f'sh_{i}_personal_tax_rate', 0) or 0)
            sh.tax_amount = int(self.request.POST.get(f'sh_{i}_tax_amount', 0) or 0)
            sh.imputation_credit = int(self.request.POST.get(f'sh_{i}_imputation_credit', 0) or 0)
            sh.insurance_base = int(self.request.POST.get(f'sh_{i}_insurance_base', 0) or 0)
            sh.supplement_premium_rate = float(self.request.POST.get(f'sh_{i}_supplement_premium_rate', 2.11) or 2.11)
            sh.supplement_premium = int(self.request.POST.get(f'sh_{i}_supplement_premium', 0) or 0)
            sh.total_tax_premium = int(self.request.POST.get(f'sh_{i}_total_tax_premium', 0) or 0)
            sh.save()
            if sh.pk:
                posted_ids.add(sh.pk)
            i += 1

        # Delete rows removed by user
        to_delete = existing_ids - posted_ids
        if to_delete:
            ShareholderDividend.objects.filter(pk__in=to_delete).delete()


class ImportShareholdersView(BusinessRequiredMixin, View):
    """AJAX endpoint: import shareholders from EquityTransaction."""

    def post(self, request, client_pk, pk):
        from modules.registration.models import ShareholderRegister
        from modules.registration.models.equity_transaction import EquityTransaction

        dividend = get_object_or_404(
            DividendTax, pk=pk, year_record__client__pk=client_pk
        )
        client = dividend.year_record.client

        import_date_str = request.POST.get('import_date', '')
        if not import_date_str:
            return JsonResponse({'error': '請選擇匯入基準日'}, status=400)

        try:
            import_date = date.fromisoformat(import_date_str)
        except ValueError:
            return JsonResponse({'error': '日期格式錯誤'}, status=400)

        # Find matching ShareholderRegister by tax_id
        tax_id = client.tax_id
        if not tax_id:
            return JsonResponse({'error': '此客戶未設定統一編號，無法匯入'}, status=400)

        register = ShareholderRegister.objects.filter(
            unified_business_no=tax_id
        ).first()
        if not register:
            return JsonResponse({
                'error': f'找不到統一編號 {tax_id} 的股東名簿，請先在登記模組建立'
            }, status=404)

        # Get all transactions up to import_date
        transactions = EquityTransaction.objects.filter(
            shareholder_register=register,
            transaction_date__lte=import_date,
        ).order_by('transaction_date', 'created_at')

        if not transactions.exists():
            return JsonResponse({
                'error': f'在 {import_date} 前找不到任何股權交易記錄'
            }, status=404)

        # Aggregate: group by (name, id_number, stock_type)
        # Increase reasons add shares, decrease reasons subtract
        DECREASE_REASONS = {
            'CAPITAL_REDUCTION', 'SELL', 'MERGER_DECREASE',
            'SPLIT_DECREASE', 'OTHER_DECREASE',
        }
        holdings = defaultdict(lambda: {
            'share_count': 0, 'total_amount': Decimal('0'),
            'id_number': '', 'stock_type': 'COMMON',
        })
        for tx in transactions:
            key = (tx.shareholder_name, tx.shareholder_id_number, tx.stock_type)
            count = tx.share_count
            amount = tx.total_amount
            if tx.transaction_reason in DECREASE_REASONS:
                count = -abs(count)
                amount = -abs(amount)
            else:
                count = abs(count)
                amount = abs(amount)
            holdings[key]['share_count'] += count
            holdings[key]['total_amount'] += amount
            holdings[key]['id_number'] = tx.shareholder_id_number
            holdings[key]['stock_type'] = tx.stock_type

        # Filter out zero or negative holdings
        active_holdings = {
            k: v for k, v in holdings.items() if v['share_count'] > 0
        }

        if not active_holdings:
            return JsonResponse({
                'error': '所有股東持股為 0，請確認交易記錄'
            }, status=404)

        # Calculate total shares for ratio
        total_shares = sum(h['share_count'] for h in active_holdings.values())

        # Clear existing and recreate
        dividend.shareholders.all().delete()
        dividend.import_date = import_date
        dividend.save(update_fields=['import_date'])

        new_shareholders = []
        for (name, id_num, stype), data in active_holdings.items():
            ratio = round(data['share_count'] / total_shares * 100, 2) if total_shares else 0
            sh = ShareholderDividend(
                dividend_tax=dividend,
                shareholder_name=name,
                id_number=id_num,
                stock_type=stype,
                share_count=data['share_count'],
                face_value=10,  # default
                share_amount=int(data['total_amount']),
                share_ratio=ratio,
            )
            new_shareholders.append(sh)

        ShareholderDividend.objects.bulk_create(new_shareholders)

        # Return updated data
        result = []
        for sh in dividend.shareholders.all():
            result.append({
                'id': str(sh.pk),
                'name': sh.shareholder_name,
                'id_number': sh.id_number,
                'stock_type': sh.stock_type,
                'share_count': sh.share_count,
                'face_value': float(sh.face_value),
                'share_amount': float(sh.share_amount),
                'share_ratio': float(sh.share_ratio),
                'dividend_amount': float(sh.dividend_amount),
                'personal_tax_rate': float(sh.personal_tax_rate),
                'tax_amount': float(sh.tax_amount),
                'imputation_credit': float(sh.imputation_credit),
                'insurance_base': float(sh.insurance_base),
                'supplement_premium_rate': float(sh.supplement_premium_rate),
                'supplement_premium': float(sh.supplement_premium),
                'total_tax_premium': float(sh.total_tax_premium),
            })

        return JsonResponse({'shareholders': result, 'import_date': import_date_str})
