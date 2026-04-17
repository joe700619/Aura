from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import ListView, DetailView, UpdateView, TemplateView
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin
from django.views import View
from django.http import HttpResponseRedirect
from django.forms import modelformset_factory
from datetime import date

from ..models import BookkeepingClient, BookkeepingYear, BookkeepingPeriod

class ProgressListView(ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    """
    記帳進度表列表視圖
    顯示所有已經建立過「記帳進度設定」的客戶。
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/progress/list.html'
    context_object_name = 'clients'
    search_fields = ['name', 'tax_id']

    def get_queryset(self):
        # 僅列出擁有「記帳進度設定」此一對一關聯的客戶
        return BookkeepingClient.objects.filter(
            bookkeeping_setting__isnull=False
        ).select_related('bookkeeping_setting').order_by('name')


class ProgressDetailView(BusinessRequiredMixin, DetailView):
    """
    記帳進度表維護介面
    顯示特定客戶某個年度下所有的期別資料，讓記帳人員可以一覽並批次編輯
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/progress/client_detail.html'
    context_object_name = 'client'

    def get_queryset(self):
        return super().get_queryset().filter(bookkeeping_setting__isnull=False).select_related('bookkeeping_setting')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object
        
        # 1. 取得該客戶目前所有的「年度」資料以作頁籤切換
        available_years = client.bookkeeping_years.all().order_by('-year')
        context['available_years'] = available_years

        # 2. 決定當前顯示「哪個年度」
        selected_year_val = self.request.GET.get('year')
        current_year_obj = None
        
        if available_years.exists():
            if selected_year_val:
                try:
                    current_year_obj = available_years.get(year=int(selected_year_val))
                except (ValueError, BookkeepingYear.DoesNotExist):
                    current_year_obj = available_years.first()
            else:
                current_year_obj = available_years.first()
                
        context['current_year_obj'] = current_year_obj

        # 3. 如果有找到當前年度，就載入它的期別 formset
        # 4. 專家系統規則與客製化設定
        from ..rules import get_all_rules
        from ..models import ClientRuleSetting
        rules = get_all_rules()
        settings = {s.rule_code: s for s in ClientRuleSetting.objects.filter(client=client)}
        expert_rules_data = []
        for r in rules:
            s = settings.get(r.code)
            expert_rules_data.append({
                'rule': r,
                'setting': s
            })
        context['expert_rules_data'] = expert_rules_data

        if current_year_obj:
            PeriodFormSet = modelformset_factory(
                BookkeepingPeriod,
                fields=('account_status', 'accounting_date', 'notes', 'sales_amount', 'tax_amount', 'input_tax', 'payable_tax', 'filing_status'),
                extra=0,
                can_delete=False
            )
            
            queryset = BookkeepingPeriod.objects.filter(year_record=current_year_obj).order_by('period_start_month')
            
            if self.request.method == 'POST':
                context['formset'] = PeriodFormSet(self.request.POST, queryset=queryset)
            else:
                context['formset'] = PeriodFormSet(queryset=queryset)

        return context
        
    def post(self, request, *args, **kwargs):
        """處理 formset 批次儲存"""
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        
        formset = context.get('formset')
        current_year_obj = context.get('current_year_obj')
        
        if formset and formset.is_valid():
            formset.save()
            messages.success(request, f'已成功儲存 {current_year_obj.year} 年度之記帳進度紀錄。')
            url = reverse('bookkeeping:progress_detail', kwargs={'pk': self.object.pk})
            return HttpResponseRedirect(f"{url}?year={current_year_obj.year}")
            
        return self.render_to_response(context)


class SaveExpertRuleSettingsView(BusinessRequiredMixin, View):
    """儲存客戶專屬的專家系統閾值設定"""
    def post(self, request, client_pk):
        from ..models import BookkeepingClient, ClientRuleSetting
        from ..rules import get_all_rules
        
        client = get_object_or_404(BookkeepingClient, pk=client_pk)
        rules = get_all_rules()
        
        for rule in rules:
            is_active_str = request.POST.get(f'rule_{rule.code}_active', 'off')
            is_active = is_active_str == 'on'
            
            threshold_str = request.POST.get(f'rule_{rule.code}_threshold', '').strip()
            threshold = None
            if threshold_str:
                try:
                    threshold = float(threshold_str)
                except ValueError:
                    pass
            
            ClientRuleSetting.objects.update_or_create(
                client=client,
                rule_code=rule.code,
                defaults={
                    'is_active': is_active,
                    'custom_threshold': threshold
                }
            )
            
        messages.success(request, '已成功更新專家系統閾值設定！')
        year_param = request.GET.get('year', '')
        url = reverse('bookkeeping:progress_detail', kwargs={'pk': client_pk})
        if year_param:
            url += f"?year={year_param}"
        return HttpResponseRedirect(url)

class AddProgressYearView(BusinessRequiredMixin, View):
    """快速建立記帳年度及對應6期數的 API"""
    
    def post(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk, bookkeeping_setting__isnull=False)
        year_val = request.POST.get('year')
        
        if not year_val or not year_val.isdigit():
            messages.error(request, '請提供有效的年度數字。')
            return redirect('bookkeeping:progress_detail', pk=pk)
            
        year_val = int(year_val)
        
        # 檢查是否已經存在此年度
        year_obj, created = BookkeepingYear.objects.get_or_create(
            client=client, 
            year=year_val
        )
        
        if created:
            # 建立6期
            months = [1, 3, 5, 7, 9, 11]
            periods_to_create = []
                
            for month in months:
                periods_to_create.append(
                    BookkeepingPeriod(
                        year_record=year_obj,
                        period_start_month=month
                    )
                )
                
            BookkeepingPeriod.objects.bulk_create(periods_to_create)
            messages.success(request, f'成功建立 {year_val} 年度。')
        else:
            messages.warning(request, f'{year_val} 年度記錄已存在。')
            
        url = reverse('bookkeeping:progress_detail', kwargs={'pk': pk})
        return HttpResponseRedirect(f"{url}?year={year_val}")


class ProgressPeriodDetailView(BusinessRequiredMixin, UpdateView):
    """
    期別詳情頁：顯示並編輯單一期的完整記帳及營業稅資料
    URL: /bookkeeping/progress/<client_pk>/period/<pk>/
    """
    model = BookkeepingPeriod
    template_name = 'bookkeeping/progress/period_detail.html'
    fields = [
        'account_status', 'accounting_date', 'notes',
        'sales_amount', 'tax_amount', 'input_tax', 'payable_tax', 'filing_status'
    ]

    def get_object(self, queryset=None):
        return get_object_or_404(
            BookkeepingPeriod,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_success_url(self):
        return reverse('bookkeeping:progress_period_detail', kwargs={
            'client_pk': self.kwargs['client_pk'],
            'pk': self.object.pk,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.object
        client = period.year_record.client
        context['client'] = client
        context['period'] = period
        context['year_obj'] = period.year_record

        # 取得針對這個期別的專家系統警報
        context['rule_alerts'] = period.rule_alerts.all().order_by('-created_at')

        # ── 累計營業稅資料 ──
        # 找同一客戶、同一年度 (民國) 的 TaxFilingYear
        from ..models import TaxFilingYear, TaxFilingPeriod as VatPeriod
        from django.db.models import Sum

        roc_year = period.year_record.year  # 民國年 (e.g. 115)
        current_start_month = period.period_start_month  # e.g. 5 代表5-6月期

        # 嘗試取得對應的營業稅年度
        vat_year = TaxFilingYear.objects.filter(
            client=client,
            year=roc_year,
        ).first()

        vat_periods_ytd = []
        vat_cumulative = {
            'sales_amount': 0,
            'tax_amount': 0,
            'input_amount': 0,
            'input_tax': 0,
            'payable_tax': 0,
        }

        if vat_year:
            # 取「期別起月 <= 當前期別起月」的所有期別，代表截至本期
            vat_periods_ytd = list(
                VatPeriod.objects.filter(
                    year_record=vat_year,
                    period_start_month__lte=current_start_month,
                ).order_by('period_start_month')
            )

            # 加總
            totals = VatPeriod.objects.filter(
                year_record=vat_year,
                period_start_month__lte=current_start_month,
            ).aggregate(
                total_sales=Sum('sales_amount'),
                total_tax=Sum('tax_amount'),
                total_input_amount=Sum('input_amount'),
                total_input_tax=Sum('input_tax'),
                total_payable=Sum('payable_tax'),
            )
            vat_cumulative = {
                'sales_amount': totals['total_sales'] or 0,
                'tax_amount': totals['total_tax'] or 0,
                'input_amount': totals['total_input_amount'] or 0,
                'input_tax': totals['total_input_tax'] or 0,
                'payable_tax': totals['total_payable'] or 0,
            }

        context['vat_periods_ytd'] = vat_periods_ytd
        context['vat_cumulative'] = vat_cumulative
        context['vat_year_found'] = vat_year is not None

        return context


class ProgressTrackerView(BusinessRequiredMixin, TemplateView):
    """
    記帳期別進度表
    讓記帳人員依年度/月份，一眼查閱所有客戶的帳務處理與申報狀況。
    """
    template_name = 'bookkeeping/progress/tracker.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 1. 所有已建立的記帳年度（去重）
        all_years = (
            BookkeepingYear.objects
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

        # 3. 讓使用者選 1-12 月，前端顯示用
        context['month_choices'] = list(range(1, 13))

        # 預設最新（最大）月份
        if not selected_month:
            # 試著抓此年度有資料的最大期別月份
            last_period = (
                BookkeepingPeriod.objects
                .filter(year_record__year=selected_year)
                .order_by('-period_start_month')
                .values_list('period_start_month', flat=True)
                .first()
            )
            selected_month = last_period or 11

        context['selected_month'] = selected_month

        # 換算成期別的起月 (1, 3, 5, 7, 9, 11)
        bimonthly_month = selected_month if selected_month % 2 == 1 else selected_month - 1

        q = self.request.GET.get('q', '').strip()
        context['q'] = q

        periods = []
        if selected_year:
            qs_filter = Q(year_record__year=selected_year, period_start_month=bimonthly_month)
            if q:
                qs_filter &= Q(year_record__client__name__icontains=q) | Q(year_record__client__tax_id__icontains=q)
            periods = list(
                BookkeepingPeriod.objects
                .filter(qs_filter)
                .select_related(
                    'year_record__client',
                    'year_record__client__bookkeeping_setting',
                    'year_record__client__bookkeeping_assistant',
                )
            )

            # 依記帳助理姓名筆劃排序
            def _assistant_sort_key(p):
                assistant = p.year_record.client.bookkeeping_assistant
                return (assistant.name if assistant else '\uFFFF',
                        p.year_record.client.name)

            periods.sort(key=_assistant_sort_key)

        # 5. 統計摘要（篩選前）
        total = len(periods)
        count_not_started  = sum(1 for p in periods if p.account_status == 'not_started')
        count_in_progress  = sum(1 for p in periods if p.account_status == 'in_progress')
        count_waiting_docs = sum(1 for p in periods if p.account_status == 'waiting_docs')
        count_completed    = sum(1 for p in periods if p.account_status == 'completed')

        context['stats'] = {
            'total': total,
            'not_started':  count_not_started,
            'in_progress':  count_in_progress,
            'waiting_docs': count_waiting_docs,
            'completed':    count_completed,
        }

        # 6. 快速篩選（server-side）
        status_filter = self.request.GET.get('filter', 'ALL')
        context['current_filter'] = status_filter
        context['filter_counts'] = {
            'ALL':          total,
            'not_started':  count_not_started,
            'in_progress':  count_in_progress,
            'waiting_docs': count_waiting_docs,
            'completed':    count_completed,
        }

        if status_filter != 'ALL':
            periods = [p for p in periods if p.account_status == status_filter]

        # 7. 分頁
        paginator = Paginator(periods, 25)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        context['periods'] = list(page_obj)
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        context['is_paginated'] = paginator.num_pages > 1
        context['current_per_page'] = 25

        context['today'] = date.today()
        context['model_app_label'] = BookkeepingPeriod._meta.app_label
        context['model_name'] = BookkeepingPeriod._meta.model_name
        return context


class RunExpertSystemView(BusinessRequiredMixin, View):
    """
    手動執行專家診斷系統的 API 端點
    URL: /bookkeeping/progress/<client_pk>/period/<pk>/run-expert/
    """
    def post(self, request, client_pk, pk):
        from ..models import BookkeepingClient, BookkeepingPeriod
        from ..services.expert_engine import ExpertEngine
        
        client = get_object_or_404(BookkeepingClient, pk=client_pk)
        period = get_object_or_404(BookkeepingPeriod, pk=pk, year_record__client=client)
        
        try:
            # 呼叫核心引擎執行檢查
            new_alerts_count = ExpertEngine.run_checks(client, period)
            
            if new_alerts_count > 0:
                messages.warning(request, f'專家診斷執行完成，發現 {new_alerts_count} 項新異常！請參考上方警示。')
            else:
                messages.success(request, '專家診斷執行完成，本期未發現新的異常情事。')
                
        except Exception as e:
            messages.error(request, f'執行專家診斷時發生錯誤: {str(e)}')
            
        # 回到期別明細頁
        return redirect('bookkeeping:progress_period_detail', client_pk=client_pk, pk=pk)
