from django.views.generic import TemplateView
from core.mixins import BusinessRequiredMixin
from django.db.models import Prefetch, Sum
from decimal import Decimal
from collections import defaultdict

from ..models.voucher import Voucher
from ..models.voucher_detail import VoucherDetail
from ..models.account import Account
from ..forms import ReportFilterForm

class JournalListView(BusinessRequiredMixin, TemplateView):
    template_name = 'report/journal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        submitted = bool(self.request.GET)
        form = ReportFilterForm(self.request.GET or None)
        context['form'] = form
        context['submitted'] = submitted

        if not submitted:
            context['month_groups'] = []
            context['total_debit'] = Decimal('0.00')
            context['total_credit'] = Decimal('0.00')
            return context

        queryset = VoucherDetail.objects.select_related('voucher', 'account').filter(voucher__status=Voucher.Status.POSTED)

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            voucher_no = form.cleaned_data.get('voucher_no')
            if start_date:
                queryset = queryset.filter(voucher__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(voucher__date__lte=end_date)
            if voucher_no:
                queryset = queryset.filter(voucher__voucher_no__icontains=voucher_no)

        queryset = queryset.order_by('voucher__date', 'voucher__voucher_no', 'id')

        month_groups = {}
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        for entry in queryset:
            month_key = entry.voucher.date.strftime('%Y年%m月')
            if month_key not in month_groups:
                month_groups[month_key] = {
                    'month': month_key,
                    'entries': [],
                    'total_debit': Decimal('0.00'),
                    'total_credit': Decimal('0.00'),
                }
            month_groups[month_key]['entries'].append(entry)
            month_groups[month_key]['total_debit'] += entry.debit
            month_groups[month_key]['total_credit'] += entry.credit
            total_debit += entry.debit
            total_credit += entry.credit

        context['month_groups'] = month_groups.values()
        context['total_debit'] = total_debit
        context['total_credit'] = total_credit
        return context

class GeneralLedgerListView(BusinessRequiredMixin, TemplateView):
    template_name = 'report/general_ledger.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        submitted = bool(self.request.GET)
        form = ReportFilterForm(self.request.GET or None)
        context['form'] = form
        context['submitted'] = submitted

        if not submitted:
            context['account_groups'] = []
            return context

        queryset = VoucherDetail.objects.select_related('voucher', 'account').filter(voucher__status=Voucher.Status.POSTED)

        start_date = None

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            voucher_no = form.cleaned_data.get('voucher_no')
            account_code_start = form.cleaned_data.get('account_code_start')
            account_code_end = form.cleaned_data.get('account_code_end')
            
            if start_date:
                queryset = queryset.filter(voucher__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(voucher__date__lte=end_date)
            if voucher_no:
                queryset = queryset.filter(voucher__voucher_no__icontains=voucher_no)
            if account_code_start:
                queryset = queryset.filter(account__code__gte=account_code_start)
            if account_code_end:
                queryset = queryset.filter(account__code__lte=account_code_end)
                
        # Group entries by Account logic
        queryset = queryset.order_by('account__code', 'voucher__date', 'voucher__voucher_no', 'id')
        
        # We need a way to group and display running balance
        account_groups = {}
        for entry in queryset:
            acc_code = entry.account.code
            if acc_code not in account_groups:
                account_groups[acc_code] = {
                    'account': entry.account,
                    'entries': [],
                    'running_balance': Decimal('0.00'),
                    'opening_balance': Decimal('0.00')
                }
                # Calculate Opening Balance BEFORE start_date if any
                if start_date:
                    prior_entries = VoucherDetail.objects.filter(
                        account=entry.account,
                        voucher__status=Voucher.Status.POSTED,
                        voucher__date__lt=start_date
                    )
                    prior_debit = prior_entries.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
                    prior_credit = prior_entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')
                    
                    # Depending on normal balance (Asset/Expense = Debit, Liability/Equity/Revenue = Credit)
                    # For simplicity, we can do Balance = Debit - Credit or adjust by Account Type
                    # Assuming normal balance for 1, 5, 6, 7 is Debit, 2, 3, 4 is Credit
                    if entry.account.code.startswith(('1', '5', '6', '7')):
                        account_groups[acc_code]['opening_balance'] = prior_debit - prior_credit
                    else:
                        account_groups[acc_code]['opening_balance'] = prior_credit - prior_debit
                
                account_groups[acc_code]['running_balance'] = account_groups[acc_code]['opening_balance']
            
            # Update Running Balance for the current iteration row
            if entry.account.code.startswith(('1', '5', '6', '7')):
                row_balance = entry.debit - entry.credit
            else:
                row_balance = entry.credit - entry.debit
                
            account_groups[acc_code]['running_balance'] += row_balance
            
            # Attach the row_balance to the entry dictionary (we make a mutable dict copy)
            account_groups[acc_code]['entries'].append({
                'date': entry.voucher.date,
                'voucher_no': entry.voucher.voucher_no,
                'voucher_id': entry.voucher.id,
                'remark': entry.remark or entry.voucher.description,
                'debit': entry.debit,
                'credit': entry.credit,
                'balance': account_groups[acc_code]['running_balance']
            })
            
        context['account_groups'] = account_groups.values()
        return context

class IncomeStatementView(BusinessRequiredMixin, TemplateView):
    template_name = 'report/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submitted = bool(self.request.GET)
        form = ReportFilterForm(self.request.GET or None)
        context['form'] = form
        context['submitted'] = submitted

        if not submitted:
            return context

        sections = {
            Account.Category.REVENUE:    {'name': '營業收入',   'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': True},
            Account.Category.COST:       {'name': '營業成本',   'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': False},
            Account.Category.EXPENSE:    {'name': '營業費用',   'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': False},
            Account.Category.NON_OP_INC: {'name': '營業外收入', 'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': True},
            Account.Category.NON_OP_EXP: {'name': '營業外支出', 'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': False},
            Account.Category.TAX:        {'name': '所得稅費用', 'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': False},
        }

        start_date = None
        end_date = None
        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')

        queryset = VoucherDetail.objects.select_related('account', 'voucher').filter(
            voucher__status=Voucher.Status.POSTED,
            account__category__in=list(sections.keys())
        )
        if start_date:
            queryset = queryset.filter(voucher__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(voucher__date__lte=end_date)

        for entry in queryset:
            section = sections[entry.account.category]
            balance = (entry.credit - entry.debit) if section['is_credit'] else (entry.debit - entry.credit)
            section['groups'][entry.account] += balance
            section['total'] += balance

        gross_profit     = sections[Account.Category.REVENUE]['total'] - sections[Account.Category.COST]['total']
        operating_profit = gross_profit - sections[Account.Category.EXPENSE]['total']
        pre_tax_income   = operating_profit + sections[Account.Category.NON_OP_INC]['total'] - sections[Account.Category.NON_OP_EXP]['total']
        net_income       = pre_tax_income - sections[Account.Category.TAX]['total']

        for key in sections:
            sections[key]['groups'] = {acc: bal for acc, bal in sections[key]['groups'].items() if bal != 0}

        context['sections']          = sections
        context['gross_profit']      = gross_profit
        context['operating_profit']  = operating_profit
        context['pre_tax_income']    = pre_tax_income
        context['net_income']        = net_income
        context['start_date']        = start_date
        context['end_date']          = end_date
        return context

class BalanceSheetView(BusinessRequiredMixin, TemplateView):
    template_name = 'report/balance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submitted = bool(self.request.GET)
        form = ReportFilterForm(self.request.GET or None)
        context['form'] = form
        context['submitted'] = submitted

        if not submitted:
            return context

        sections = {
            Account.Category.ASSET:     {'name': '資產', 'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': False},
            Account.Category.LIABILITY: {'name': '負債', 'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': True},
            Account.Category.EQUITY:    {'name': '權益', 'groups': defaultdict(Decimal), 'total': Decimal('0.00'), 'is_credit': True},
        }

        end_date = None
        if form.is_valid():
            end_date = form.cleaned_data.get('end_date')

        # Query all posted details up to end_date
        bs_categories = list(sections.keys())
        
        # 1. Assets, Liabilities, Equity (excluding Net Income for the period)
        queryset = VoucherDetail.objects.select_related('account', 'voucher').filter(
            voucher__status=Voucher.Status.POSTED,
            account__category__in=bs_categories
        )
        if end_date:
            queryset = queryset.filter(voucher__date__lte=end_date)
            
        for entry in queryset:
            cat = entry.account.category
            section = sections[cat]
            if section['is_credit']:
                balance = entry.credit - entry.debit
            else:
                balance = entry.debit - entry.credit
                
            section['groups'][entry.account] += balance
            section['total'] += balance
            
        # 2. Calculate Net Income (Retained Earnings) dynamically
        pl_categories = [Account.Category.REVENUE, Account.Category.COST, Account.Category.EXPENSE, 
                         Account.Category.NON_OP_INC, Account.Category.NON_OP_EXP, Account.Category.TAX]
        
        pl_queryset = VoucherDetail.objects.select_related('account', 'voucher').filter(
            voucher__status=Voucher.Status.POSTED,
            account__category__in=pl_categories
        )
        if end_date:
            pl_queryset = pl_queryset.filter(voucher__date__lte=end_date)
            
        net_income = Decimal('0.00')
        for entry in pl_queryset:
            cat = entry.account.category
            # Revenue & Non Op Inc = Credit Normal. Others = Debit Normal
            if cat in [Account.Category.REVENUE, Account.Category.NON_OP_INC]:
                net_income += (entry.credit - entry.debit)
            else:
                net_income -= (entry.debit - entry.credit)
                
        # Inject Net Income into Equity section
        if net_income != 0:
            # We create a dummy object for the template to render
            dummy_account = type('DummyAccount', (), {'code': '3999', 'name': '本期損益', 'category': Account.Category.EQUITY})()
            sections[Account.Category.EQUITY]['groups'][dummy_account] = net_income
            sections[Account.Category.EQUITY]['total'] += net_income
            
        # Clean up empty accounts
        for key in sections:
            sections[key]['groups'] = {acc: bal for acc, bal in sections[key]['groups'].items() if bal != 0}
            
        total_liab_and_equity = sections[Account.Category.LIABILITY]['total'] + sections[Account.Category.EQUITY]['total']
        is_balanced = (sections[Account.Category.ASSET]['total'] == total_liab_and_equity)
            
        context['sections']              = sections
        context['total_assets']          = sections[Account.Category.ASSET]['total']
        context['total_liab_and_equity'] = total_liab_and_equity
        context['is_balanced']           = is_balanced
        context['end_date']              = end_date
        return context

class SubsidiaryLedgerView(BusinessRequiredMixin, TemplateView):
    template_name = 'report/subsidiary_ledger.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..forms import SubsidiaryLedgerFilterForm
        
        form = SubsidiaryLedgerFilterForm(self.request.GET or None)
        
        start_date = None
        end_date = None
        account_code = None
        company_id = None
        
        # Only process if valid and an account code is chosen
        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            account_code = form.cleaned_data.get('account_code')
            company_id = form.cleaned_data.get('company_id')
            
        if not account_code:
            context['form'] = form
            context['company_groups'] = []
            return context
            
        # Base Query for the selected account
        queryset = VoucherDetail.objects.select_related('voucher', 'account').filter(
            voucher__status=Voucher.Status.POSTED,
            account__code__startswith=account_code
        ).exclude(company_id__exact='') # Must have a company_id for subsidiary ledger
        
        if company_id:
            queryset = queryset.filter(company_id__icontains=company_id)
            
        if start_date:
            queryset = queryset.filter(voucher__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(voucher__date__lte=end_date)
            
        # Order chronologically
        queryset = queryset.order_by('company_id', 'voucher__date', 'voucher__voucher_no', 'id')
        
        company_groups = {}
        target_account = Account.objects.filter(code=account_code).first()
        is_debit_normal = True
        if target_account and not target_account.code.startswith(('1', '5', '6', '7')):
            is_debit_normal = False
            
        for entry in queryset:
            c_id = entry.company_id
            if c_id not in company_groups:
                company_groups[c_id] = {
                    'company_id': c_id,
                    'account_name': entry.account.name,
                    'entries': [],
                    'opening_balance': Decimal('0.00'),
                    'running_balance': Decimal('0.00')
                }
                
                # Calculate Opening Balance BEFORE start_date if any for this specific company
                if start_date:
                    prior_entries = VoucherDetail.objects.filter(
                        account__code__startswith=account_code,
                        company_id=c_id,
                        voucher__status=Voucher.Status.POSTED,
                        voucher__date__lt=start_date
                    )
                    prior_debit = prior_entries.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
                    prior_credit = prior_entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')
                    
                    if is_debit_normal:
                        company_groups[c_id]['opening_balance'] = prior_debit - prior_credit
                    else:
                        company_groups[c_id]['opening_balance'] = prior_credit - prior_debit
                        
                company_groups[c_id]['running_balance'] = company_groups[c_id]['opening_balance']
                
            # Update Running Balance
            if is_debit_normal:
                row_balance = entry.debit - entry.credit
            else:
                row_balance = entry.credit - entry.debit
                
            company_groups[c_id]['running_balance'] += row_balance
            
            company_groups[c_id]['entries'].append({
                'date': entry.voucher.date,
                'voucher_no': entry.voucher.voucher_no,
                'voucher_id': entry.voucher.id,
                'remark': entry.remark or entry.voucher.description,
                'debit': entry.debit,
                'credit': entry.credit,
                'balance': company_groups[c_id]['running_balance']
            })
            
        context['form'] = form
        context['company_groups'] = company_groups.values()
        context['target_account'] = target_account
        
        return context
