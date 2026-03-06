from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import BookkeepingClient, TaxFilingSetting

class BusinessTaxListView(LoginRequiredMixin, ListView):
    """
    營業稅申報列表視圖
    顯示所有已經建立過「營業稅申報設定」的客戶，方便快速進入各期申報維護。
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/business_tax/list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        # 僅列出擁有「營業稅申報設定」此一對一關聯的客戶
        return BookkeepingClient.objects.filter(
            tax_setting__isnull=False
        ).select_related('tax_setting').order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 可以加上額外的統計或過濾選項到 Context 中
        return context
