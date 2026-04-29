from django.views.generic import DetailView
from core.mixins import BusinessRequiredMixin
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.http import HttpResponseRedirect
from django.forms import modelformset_factory, FileInput

from ..models import BookkeepingClient, TaxFilingYear, TaxFilingPeriod, TaxFilingSetting

class BusinessTaxDetailView(BusinessRequiredMixin, DetailView):
    """
    營業稅申報維護介面
    顯示特定客戶某個年度下所有的期別資料，讓記帳人員可以一覽並批次編輯
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/business_tax/client_detail.html'
    context_object_name = 'client'

    def get_queryset(self):
        # 僅限擁有營業稅設定檔的客戶才允許進入維護畫面
        return super().get_queryset().filter(tax_setting__isnull=False).select_related('tax_setting')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object
        
        # 1. 取得該客戶目前所有的「年度」資料以作頁籤切換
        available_years = client.tax_years.all().order_by('-year')
        context['available_years'] = available_years

        # 2. 決定當前顯示「哪個年度」
        # 如果 Query String 有帶 `?year=113` 就優先使用；否則預設使用最新那一年。
        selected_year_val = self.request.GET.get('year')
        current_year_obj = None
        
        if available_years.exists():
            if selected_year_val:
                try:
                    current_year_obj = available_years.get(year=int(selected_year_val))
                except (ValueError, TaxFilingYear.DoesNotExist):
                    current_year_obj = available_years.first()
            else:
                current_year_obj = available_years.first()
                
        context['current_year_obj'] = current_year_obj

        # 3. 如果有找到當前年度，就載入它的期別 formset
        if current_year_obj:
            PeriodFormSet = modelformset_factory(
                TaxFilingPeriod,
                fields=('invoice_received_date', 'sales_amount', 'tax_amount', 'input_tax', 'retained_tax', 'payable_tax', 'filing_date', 'filing_document'),
                widgets={
                    'filing_document': FileInput(),
                },
                extra=0,
                can_delete=False
            )
            
            queryset = TaxFilingPeriod.objects.filter(year_record=current_year_obj).order_by('period_start_month')
            
            if self.request.method == 'POST':
                context['formset'] = PeriodFormSet(self.request.POST, self.request.FILES, queryset=queryset)
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
            messages.success(request, f'已成功儲存 {current_year_obj.year} 年度之營業稅申報紀錄。')
            # 重新導向回同年份的頁面
            url = reverse('bookkeeping:business_tax_detail', kwargs={'pk': self.object.pk})
            return HttpResponseRedirect(f"{url}?year={current_year_obj.year}")
            
        return self.render_to_response(context)


class AddBusinessTaxYearView(BusinessRequiredMixin, View):
    """快速建立申報年度及對應期數的 API/Action"""
    
    def post(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk, tax_setting__isnull=False)
        year_val = request.POST.get('year')
        
        if not year_val or not year_val.isdigit():
            messages.error(request, '請提供有效的年度數字。')
            return redirect('bookkeeping:business_tax_detail', pk=pk)
            
        year_val = int(year_val)
        
        # 檢查是否已經存在此年度
        year_obj, created = TaxFilingYear.objects.get_or_create(
            client=client, 
            year=year_val
        )
        
        if created:
            # 根據申報頻率建立對應期數
            freq = client.tax_setting.filing_frequency
            
            periods_to_create = []
            if freq == TaxFilingSetting.FilingFrequency.BIMONTHLY:
                # 單月申報，一次建立 6 期 (1, 3, 5, 7, 9, 11)
                months = [1, 3, 5, 7, 9, 11]
            else:
                # 按月申報，一次建立 12 期 (1-12)
                months = list(range(1, 13))
                
            for month in months:
                periods_to_create.append(
                    TaxFilingPeriod(
                        year_record=year_obj,
                        period_start_month=month
                    )
                )
                
            TaxFilingPeriod.objects.bulk_create(periods_to_create)
            messages.success(request, f'成功建立 {year_val} 年度。')
        else:
            messages.warning(request, f'{year_val} 年度記錄已存在。')
            
        url = reverse('bookkeeping:business_tax_detail', kwargs={'pk': pk})
        return HttpResponseRedirect(f"{url}?year={year_val}")


class SaveTaxSettingsView(BusinessRequiredMixin, View):
    """儲存申報設定卡片的設定值 (notification_method, payment_method, filing_frequency)"""

    def post(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk, tax_setting__isnull=False)
        setting = client.tax_setting

        allowed_frequency = [c[0] for c in TaxFilingSetting.FilingFrequency.choices]

        filing_frequency = request.POST.get('filing_frequency', '').strip()

        if filing_frequency in allowed_frequency:
            setting.filing_frequency = filing_frequency

        setting.save(update_fields=['filing_frequency'])
        messages.success(request, '申報設定已儲存。')
        return redirect('bookkeeping:business_tax_detail', pk=pk)
