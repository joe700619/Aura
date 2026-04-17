import json
from core.mixins import BusinessRequiredMixin
import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from ..models import BookkeepingClient
from ..models.income_tax import IncomeTaxYear
from ..models.income_tax_media import IncomeTaxMediaData
from ..services.income_tax_media_parser import (
    parse_001_file, apply_parsed_data, MediaFileParseError,
)

logger = logging.getLogger(__name__)


class IncomeTaxMediaDetailView(BusinessRequiredMixin, DetailView):
    """
    第 5 區塊：申報書媒體檔完整管理頁面
    URL: /bookkeeping/income-tax/<client_pk>/media/<pk>/
    """
    model = IncomeTaxMediaData
    template_name = 'bookkeeping/income_tax/media_data_detail.html'
    context_object_name = 'media_data'

    def get_object(self, queryset=None):
        return get_object_or_404(
            IncomeTaxMediaData,
            pk=self.kwargs['pk'],
            year_record__client__pk=self.kwargs['client_pk'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        media_data = self.object
        client = media_data.year_record.client

        context['client'] = client
        context['year_obj'] = media_data.year_record
        context['setting'] = getattr(client, 'income_tax_setting', None)
        return context


class IncomeTaxMediaUploadView(BusinessRequiredMixin, View):
    """
    上傳 001 媒體檔並觸發解析
    POST: /bookkeeping/income-tax/<client_pk>/media/<pk>/upload/
    """

    def post(self, request, client_pk, pk):
        media_data = get_object_or_404(
            IncomeTaxMediaData,
            pk=pk,
            year_record__client__pk=client_pk,
        )

        uploaded_file = request.FILES.get('raw_file')
        if not uploaded_file:
            messages.error(request, '請選擇要上傳的 001 檔案。')
            return self._redirect(client_pk, pk)

        # 儲存原始檔案
        media_data.raw_file = uploaded_file
        media_data.save(update_fields=['raw_file'])

        # 解析檔案
        try:
            # 重新開啟檔案進行解析
            media_data.raw_file.open('rb')
            parsed_data = parse_001_file(media_data.raw_file)
            media_data.raw_file.close()

            # 將解析結果寫入 Model
            apply_parsed_data(media_data, parsed_data)
            messages.success(request, '001 媒體檔上傳並解析成功。')

        except MediaFileParseError as e:
            logger.error(f'001 媒體檔解析失敗: {e}')
            messages.error(request, f'001 媒體檔解析失敗：{e}')
        except Exception as e:
            logger.exception(f'001 媒體檔解析發生未預期錯誤: {e}')
            messages.error(request, f'解析過程發生錯誤：{e}')

        return self._redirect(client_pk, pk)

    def _redirect(self, client_pk, pk):
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(
            reverse('bookkeeping:income_tax_media_detail', kwargs={
                'client_pk': client_pk, 'pk': pk,
            })
        )


class IncomeTaxMediaSlideoverAPI(BusinessRequiredMixin, View):
    """
    JSON API：供 slide-over panel 查詢特定年度的解析資料
    GET: /bookkeeping/api/income-tax/<client_pk>/media-data/?year=113
    """

    def get(self, request, client_pk):
        client = get_object_or_404(BookkeepingClient, pk=client_pk)
        year = request.GET.get('year')

        if not year:
            return JsonResponse({'error': '缺少 year 參數'}, status=400)

        try:
            year_int = int(year)
        except (ValueError, TypeError):
            return JsonResponse({'error': '年度格式錯誤'}, status=400)

        # 查詢指定年度
        try:
            year_record = IncomeTaxYear.objects.get(client=client, year=year_int)
            media_data = year_record.media_data
        except (IncomeTaxYear.DoesNotExist, IncomeTaxMediaData.DoesNotExist):
            return JsonResponse({
                'found': False,
                'year': year_int,
                'message': f'{year_int} 年度尚無申報書媒體檔資料',
            })

        # 取得所有可用年度（供前端年度切換下拉使用）
        available_years = list(
            client.income_tax_years
            .order_by('-year')
            .values_list('year', flat=True)
        )

        data = {
            'found': True,
            'year': year_int,
            'is_parsed': media_data.is_parsed,
            'parsed_at': media_data.parsed_at.isoformat() if media_data.parsed_at else None,
            'available_years': available_years,
            'fields': {
                'industry_code': media_data.industry_code,
                'industry_name': media_data.industry_name,
                'gross_revenue': int(media_data.gross_revenue),
                'cost_of_goods': int(media_data.cost_of_goods),
                'gross_profit': int(media_data.gross_profit),
                'operating_expenses': int(media_data.operating_expenses),
                'net_operating_income': int(media_data.net_operating_income),
                'non_operating_income': int(media_data.non_operating_income),
                'non_operating_expense': int(media_data.non_operating_expense),
                'pre_tax_income': int(media_data.pre_tax_income),
                'taxable_income': int(media_data.taxable_income),
                'annual_tax': int(media_data.annual_tax),
                'provisional_paid': int(media_data.provisional_paid),
                'withholding_paid': int(media_data.withholding_paid),
                'self_pay': int(media_data.self_pay),
                'undistributed_earnings': int(media_data.undistributed_earnings),
                'undistributed_surtax': int(media_data.undistributed_surtax),
            },
            'media_detail_url': reverse('bookkeeping:income_tax_media_detail', kwargs={
                'client_pk': client_pk, 'pk': media_data.pk,
            }),
        }
        return JsonResponse(data)
