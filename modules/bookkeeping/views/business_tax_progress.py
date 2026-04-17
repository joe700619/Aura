from django.views.generic import TemplateView
from core.mixins import BusinessRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import date

from ..models import TaxFilingYear, TaxFilingPeriod, BookkeepingClient


# 只顯示需要申報營業稅的服務類型（排除執行業務與專營投資公司）
VAT_SERVICE_TYPES = [
    BookkeepingClient.ServiceType.VAT_BUSINESS,
    BookkeepingClient.ServiceType.MIXED_DIRECT,
    BookkeepingClient.ServiceType.MIXED_RATIO,
]


class BusinessTaxProgressView(BusinessRequiredMixin, TemplateView):
    """
    申報期別進度表
    讓記帳人員依年度/月份，一眼查閱所有客戶的申報與繳稅狀況。
    """
    template_name = 'bookkeeping/business_tax/progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 提供 model_app_label / model_name 讓 list_view 的動作按鈕 (Excel export) 正常運作
        context['model_app_label'] = 'bookkeeping'
        context['model_name'] = 'taxfilingperiod'

        # 1. 所有已建立的申報年度（去重）
        all_years = (
            TaxFilingYear.objects
            .order_by('-year')
            .values_list('year', flat=True)
            .distinct()
        )
        context['available_years'] = list(all_years)

        # 2. 讀取篩選條件（GET 參數）
        try:
            selected_year = int(self.request.GET.get('year', 0))
        except (ValueError, TypeError):
            selected_year = 0

        try:
            selected_month = int(self.request.GET.get('month', 0))
        except (ValueError, TypeError):
            selected_month = 0

        # 預設最新的年度
        if not selected_year and all_years:
            selected_year = list(all_years)[0]

        context['selected_year'] = selected_year

        # 3. 讓使用者選 1-12 月，方便不管是按月申報或是按期申報都能查詢
        context['month_choices'] = list(range(1, 13))

        # 預設最新（最大）月份
        if not selected_month:
            # 試著抓此年度有資料的最大期別月份
            last_period = (
                TaxFilingPeriod.objects
                .filter(year_record__year=selected_year)
                .order_by('-period_start_month')
                .values_list('period_start_month', flat=True)
                .first()
            )
            selected_month = last_period or 11  # 預設 11 月

        context['selected_month'] = selected_month

        # 4. 查詢當月的申報明細
        # 對「按月申報」客戶，period_start_month == selected_month
        # 對「單月申報(雙月)」客戶，period_start_month 必須是奇數月，
        #   所以如果使用者選的是偶數月，我們換算成前一個奇數月
        bimonthly_month = selected_month if selected_month % 2 == 1 else selected_month - 1

        q = self.request.GET.get('q', '').strip()
        context['q'] = q

        periods = []
        if selected_year:
            qs_filter = Q(
                year_record__year=selected_year,
                period_start_month__in=[selected_month, bimonthly_month],
                year_record__client__service_type__in=VAT_SERVICE_TYPES,
                year_record__client__is_deleted=False,
            )
            if q:
                qs_filter &= Q(year_record__client__name__icontains=q) | Q(year_record__client__tax_id__icontains=q)
            periods = list(
                TaxFilingPeriod.objects
                .filter(qs_filter)
                .select_related(
                    'year_record__client',
                    'year_record__client__tax_setting',
                    'year_record__client__bookkeeping_assistant',
                )
                .order_by('year_record__client__bookkeeping_assistant__name', 'year_record__client__name')
            )

            # 去重：若一個客戶同時符合兩個月份比對（例如 monthly 的 11 月 & bimonthly 的 11 月），只保留各客戶一筆
            seen_clients = set()
            unique_periods = []
            for p in periods:
                cid = p.year_record.client.pk
                if cid not in seen_clients:
                    seen_clients.add(cid)
                    unique_periods.append(p)

            # 依記帳助理姓名筆劃排序（locale 不支援中文筆劃，改以 Unicode 碼位近似，
            # 在純中文姓名環境下與發音排序差異不大；要精確筆劃需第三方套件）
            def _assistant_sort_key(p):
                assistant = p.year_record.client.bookkeeping_assistant
                return (assistant.name if assistant else '\uFFFF',  # 無助理排最後
                        p.year_record.client.name)

            unique_periods.sort(key=_assistant_sort_key)

        # 5. 統計摘要（篩選前，反映該月全部筆數）
        total = len(unique_periods)
        count_not_notified = sum(1 for p in unique_periods if p.filing_status == TaxFilingPeriod.FilingStatus.NOT_NOTIFIED)
        count_waiting = sum(1 for p in unique_periods if p.filing_status == TaxFilingPeriod.FilingStatus.WAITING)
        count_paid = sum(1 for p in unique_periods if p.filing_status == TaxFilingPeriod.FilingStatus.PAID)
        count_no_payment = sum(1 for p in unique_periods if p.filing_status == TaxFilingPeriod.FilingStatus.NO_PAYMENT_NEEDED)
        count_replied = sum(1 for p in unique_periods if p.filing_status in (
            TaxFilingPeriod.FilingStatus.AUTO_REPLIED,
            TaxFilingPeriod.FilingStatus.MANUALLY_REPLIED,
        ))

        context['stats'] = {
            'total': total,
            'not_notified': count_not_notified,
            'waiting': count_waiting,
            'replied': count_replied,
            'paid': count_paid,
            'no_payment': count_no_payment,
        }

        # 6. 狀態快速篩選（server-side）
        status_filter = self.request.GET.get('filter', 'ALL')
        context['current_filter'] = status_filter
        context['filter_counts'] = {
            'ALL':              total,
            'not_notified':     count_not_notified,
            'waiting':          count_waiting,
            'paid':             count_paid,
            'no_payment_needed': count_no_payment,
        }

        if status_filter != 'ALL':
            unique_periods = [p for p in unique_periods if p.filing_status == status_filter]

        # 7. 分頁
        paginator = Paginator(unique_periods, 25)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        context['periods'] = list(page_obj)
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        context['is_paginated'] = paginator.num_pages > 1
        context['current_per_page'] = 25

        context['today'] = date.today()
        return context
