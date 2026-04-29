from datetime import date
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import ListView, TemplateView
from core.mixins import BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin
from ..models import BookkeepingClient
from ..models.income_tax import ProvisionalTax, WithholdingTax, DividendTax, IncomeTaxFiling, IncomeTaxYear


class IncomeTaxListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    """
    所得稅申報列表視圖
    顯示所有已建立「所得稅申報設定」的客戶
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/income_tax/list.html'
    context_object_name = 'clients'
    search_fields = ['name', 'tax_id']
    paginate_by = 25
    filter_choices = {
        'book_review':     {'income_tax_setting__filing_method': 'book_review'},
        'standard':        {'income_tax_setting__filing_method': 'standard'},
        'industry_profit': {'income_tax_setting__filing_method': 'industry_profit'},
        'cpa_certified':   {'income_tax_setting__filing_method': 'cpa_certified'},
        'audit':           {'income_tax_setting__filing_method': 'audit'},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().filter(
            income_tax_setting__isnull=False,
            acceptance_status='active',
        ).select_related('income_tax_setting', 'bookkeeping_assistant').order_by('name')

    def _base_qs_for_counts(self):
        return BookkeepingClient.objects.filter(
            is_deleted=False,
            income_tax_setting__isnull=False,
            acceptance_status='active',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fc = context['filter_counts']
        context['count_book_review']     = fc['book_review']
        context['count_standard']        = fc['standard']
        context['count_industry_profit'] = fc['industry_profit']
        context['count_cpa_certified']   = fc['cpa_certified']
        context['count_audit']           = fc['audit']
        return context


class IncomeTaxProgressView(BusinessRequiredMixin, TemplateView):
    """
    所得稅申報進度表
    依年度 + tab 顯示單一申報項目（暫繳/扣繳/股利/所得稅）的狀態，
    支援 server-side 狀態篩選與分頁。
    """
    template_name = 'bookkeeping/income_tax/progress.html'

    _TAB_MODELS = {
        'provisional': (ProvisionalTax,   'provisionaltax'),
        'withholding': (WithholdingTax,   'withholdingtax'),
        'dividend':    (DividendTax,      'dividendtax'),
        'filing':      (IncomeTaxFiling,  'incometaxfiling'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_app_label'] = 'bookkeeping'

        # 1. 可用年度
        all_years = (
            IncomeTaxYear.objects
            .order_by('-year')
            .values_list('year', flat=True)
            .distinct()
        )
        context['available_years'] = list(all_years)

        # 2. 年度
        try:
            selected_year = int(self.request.GET.get('year', 0))
        except (ValueError, TypeError):
            selected_year = 0
        if not selected_year and all_years:
            selected_year = list(all_years)[0]
        context['selected_year'] = selected_year

        # 3. 當前 tab
        active_tab = self.request.GET.get('tab', 'provisional')
        if active_tab not in self._TAB_MODELS:
            active_tab = 'provisional'
        context['active_tab'] = active_tab

        model_class, model_name = self._TAB_MODELS[active_tab]
        context['model_name'] = model_name

        # 4. 搜尋
        q = self.request.GET.get('q', '').strip()
        context['q'] = q

        # 5. 只 query 當前 tab 的資料
        base_filter = dict(
            year_record__year=selected_year,
            year_record__client__is_deleted=False,
        )
        q_filter = (
            Q(year_record__client__name__icontains=q) | Q(year_record__client__tax_id__icontains=q)
        ) if q else Q()

        all_items = list(
            model_class.objects
            .filter(**base_filter)
            .filter(q_filter)
            .select_related('year_record__client', 'year_record__client__bookkeeping_assistant')
            .order_by(
                'year_record__client__bookkeeping_assistant__name',
                'year_record__client__name',
            )
        )

        # 6. 計算各狀態筆數（篩選前）
        total = len(all_items)
        count_not_notified = sum(1 for p in all_items if p.filing_status == 'not_notified')
        count_waiting      = sum(1 for p in all_items if p.filing_status == 'waiting')
        count_paid         = sum(1 for p in all_items if p.filing_status == 'paid')
        count_no_payment   = sum(1 for p in all_items if p.filing_status == 'no_payment_needed')

        status_filter = self.request.GET.get('filter', 'ALL')
        context['current_filter'] = status_filter
        context['filter_counts'] = {
            'ALL':              total,
            'not_notified':     count_not_notified,
            'waiting':          count_waiting,
            'paid':             count_paid,
            'no_payment_needed': count_no_payment,
        }

        # 7. 套用狀態篩選
        if status_filter != 'ALL':
            all_items = [p for p in all_items if p.filing_status == status_filter]

        # 8. 分頁
        paginator = Paginator(all_items, 25)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        context['periods'] = list(page_obj)
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        context['is_paginated'] = paginator.num_pages > 1
        context['current_per_page'] = 25

        context['today'] = date.today()
        return context
