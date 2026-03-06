from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import BookkeepingClient
from ..models.income_tax import IncomeTaxSetting


class IncomeTaxListView(LoginRequiredMixin, ListView):
    """
    所得稅申報列表視圖
    顯示所有已建立「所得稅申報設定」的客戶
    """
    model = BookkeepingClient
    template_name = 'bookkeeping/income_tax/list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        return BookkeepingClient.objects.filter(
            income_tax_setting__isnull=False
        ).select_related('income_tax_setting').order_by('name')
