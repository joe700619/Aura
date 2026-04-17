from django.views.generic import DetailView, View
from core.mixins import BusinessRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from ..models import BookkeepingClient
from ..models.income_tax import (
    IncomeTaxSetting, IncomeTaxYear,
    ProvisionalTax, WithholdingTax, WithholdingDetail,
    DividendTax, ShareholderDividend,
    IncomeTaxFiling,
)
from ..models.income_tax_media import IncomeTaxMediaData


class IncomeTaxClientDetailView(BusinessRequiredMixin, DetailView):
    """
    所得稅申報維護介面
    顯示特定客戶某個年度下的 4 個申報項目卡片
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/income_tax/client_detail.html'
    context_object_name = 'client'

    def get_queryset(self):
        return super().get_queryset().filter(
            income_tax_setting__isnull=False
        ).select_related('income_tax_setting')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object

        # 1. 所有年度
        available_years = client.income_tax_years.all().order_by('-year')
        context['available_years'] = available_years

        # 2. 當前年度
        selected_year_val = self.request.GET.get('year')
        current_year_obj = None

        if available_years.exists():
            if selected_year_val:
                try:
                    current_year_obj = available_years.get(year=int(selected_year_val))
                except (ValueError, IncomeTaxYear.DoesNotExist):
                    current_year_obj = available_years.first()
            else:
                current_year_obj = available_years.first()

        context['current_year_obj'] = current_year_obj

        # 3. 載入 5 個子項目
        if current_year_obj:
            try:
                context['provisional'] = current_year_obj.provisional_tax
            except ProvisionalTax.DoesNotExist:
                context['provisional'] = None
            try:
                context['withholding'] = current_year_obj.withholding_tax
            except WithholdingTax.DoesNotExist:
                context['withholding'] = None
            try:
                context['dividend'] = current_year_obj.dividend_tax
            except DividendTax.DoesNotExist:
                context['dividend'] = None
            try:
                context['income_filing'] = current_year_obj.income_tax_filing
            except IncomeTaxFiling.DoesNotExist:
                context['income_filing'] = None
            try:
                context['media_data'] = current_year_obj.media_data
            except IncomeTaxMediaData.DoesNotExist:
                context['media_data'] = None

        context['setting'] = getattr(client, 'income_tax_setting', None)
        return context


class AddIncomeTaxYearView(BusinessRequiredMixin, View):
    """新增所得稅年度"""
    def post(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk)
        year = request.POST.get('year')

        if year:
            try:
                year_int = int(year)
                obj, created = IncomeTaxYear.objects.get_or_create(
                    client=client, year=year_int
                )
                if created:
                    messages.success(request, f'已新增 {year_int} 年度所得稅資料。')
                else:
                    messages.info(request, f'{year_int} 年度已存在。')
            except ValueError:
                messages.error(request, '年度格式錯誤。')

        return HttpResponseRedirect(
            reverse('bookkeeping:income_tax_detail', kwargs={'pk': pk})
            + f'?year={year}'
        )


class SaveIncomeTaxSettingsView(BusinessRequiredMixin, View):
    """儲存所得稅設定"""
    def post(self, request, pk):
        client = get_object_or_404(BookkeepingClient, pk=pk)
        setting, _ = IncomeTaxSetting.objects.get_or_create(client=client)

        setting.filing_method = request.POST.get('filing_method', setting.filing_method)
        setting.notification_method = request.POST.get('notification_method', setting.notification_method)
        setting.payment_method = request.POST.get('payment_method', setting.payment_method)
        setting.save()

        messages.success(request, '所得稅設定已儲存。')
        year = request.POST.get('current_year', '')
        redirect_url = reverse('bookkeeping:income_tax_detail', kwargs={'pk': pk})
        if year:
            redirect_url += f'?year={year}'
        return HttpResponseRedirect(redirect_url)
