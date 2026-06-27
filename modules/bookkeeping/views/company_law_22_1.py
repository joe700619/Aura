"""公司法22-1申報 專用管理頁。

列出所有勾選「由本所申報 22-1」的記帳客戶（唯一真相＝記帳客戶旗標），
並提供「批次產生本年度申報記錄」動作：下推到登記模組建 CompanyFiling +
當年度 FilingHistory（idempotent）。500 服務費不在此收，由 5 月年度帳單批次自動帶入。
"""
from datetime import date

from django.views import View
from django.views.generic import ListView
from django.http import JsonResponse

from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin
from ..models import BookkeepingClient


class CompanyLaw221ListView(SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    """勾選 22-1 的記帳客戶清單，標示本年度是否已建申報記錄。"""

    model = BookkeepingClient
    template_name = 'bookkeeping/company_law_22_1/list.html'
    context_object_name = 'clients'
    paginate_by = 25
    search_fields = ['name', 'tax_id']
    queryset = (
        BookkeepingClient.objects
        .filter(is_deleted=False, company_act_22_1_filing=True)
        .select_related('bookkeeping_assistant')
        .order_by('name')
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from modules.registration.services import get_ubns_with_annual_filing
        current_year = date.today().year
        context['current_year'] = current_year
        # 一條 query 取「今年已建記錄」的統編集合，模板逐列用 `in` 判斷（無 N+1）
        context['done_ubns'] = get_ubns_with_annual_filing(current_year)
        return context


class CompanyLaw221BatchGenerateView(BusinessRequiredMixin, View):
    """POST：派發批次 task，為所有勾選 22-1 的記帳客戶建本年度申報記錄。

    動作型 view，顯式宣告權限（需有新增登記申報資料的權限把關）。
    """
    required_perms = 'registration.add_companyfiling'

    def post(self, request):
        try:
            year = int(request.POST.get('year') or date.today().year)
        except (ValueError, TypeError):
            return JsonResponse({'error': '無效的年度'}, status=400)

        from modules.bookkeeping.tasks import generate_22_1_filings_batch
        async_result = generate_22_1_filings_batch.delay(year=year)
        return JsonResponse({
            'success': True,
            'task_id': async_result.id,
            'message': f'已開始批次產生 {year} 年度 22-1 申報記錄（背景處理中），稍後重新整理查看狀態。',
        })
