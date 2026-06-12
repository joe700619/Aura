"""後台（事務所端）勞務報酬單管理。

客戶在 client portal 建立勞報單並上傳繳款憑證；
本頁供同仁跨客戶檢視繳納狀態、代客戶上傳憑證、人工標記已繳納。
"""
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from core.mixins import (
    BusinessRequiredMixin, FilterMixin, ListActionMixin,
    ModelPermissionMixin, SearchMixin,
)
from ..models import ServiceRemuneration


class ServiceRemunerationListView(
    ListActionMixin, FilterMixin, SearchMixin,
    BusinessRequiredMixin, ModelPermissionMixin, ListView,
):
    model = ServiceRemuneration
    template_name = 'bookkeeping/service_remuneration/list.html'
    context_object_name = 'records'
    paginate_by = 50
    search_fields = ['recipient_name', 'id_number', 'client__name', 'client__tax_id']
    filter_choices = {
        'WH_PENDING': {'withholding_payment_status': ServiceRemuneration.PaymentSlipStatus.PENDING},
        'PREM_PENDING': {'premium_payment_status': ServiceRemuneration.PaymentSlipStatus.PENDING},
        'UNCONFIRMED': {'confirmation_status': ServiceRemuneration.ConfirmationStatus.PENDING},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().select_related('client').order_by(
            '-filing_date', '-created_at',
        )


def _can_change_remuneration(user):
    return user.is_superuser or user.has_perm('bookkeeping.change_serviceremuneration')


def _redirect_back(request):
    return redirect(request.META.get('HTTP_REFERER') or reverse('bookkeeping:service_remuneration_list'))


class ServiceRemunerationStaffUploadSlipView(BusinessRequiredMixin, View):
    """同仁代客戶上傳扣繳/補充保費繳款單。狀態由 model 存檔時自動同步為已上傳。"""

    def post(self, request, pk, *args, **kwargs):
        if not _can_change_remuneration(request.user):
            return HttpResponseForbidden('無修改勞務報酬單的權限')
        obj = get_object_or_404(ServiceRemuneration, pk=pk, is_deleted=False)
        f = request.FILES.get('slip')
        if not f:
            return HttpResponseBadRequest('未選擇檔案')

        if request.POST.get('slip_type') == 'supplementary':
            obj.supplementary_payment_slip = f
        else:
            obj.withholding_payment_slip = f
        obj.save()
        messages.success(request, f'已為 {obj.client.name}／{obj.recipient_name} 上傳繳款單')
        return _redirect_back(request)


class ServiceRemunerationMarkPaidView(BusinessRequiredMixin, View):
    """人工標記已繳納 / 取消標記（客戶以紙本等方式確認繳款、不上傳憑證時用）。

    標記後狀態為 MANUAL_PAID，model 重算時會保留；
    取消標記則回到待繳納（若仍有應繳金額）。
    """

    def post(self, request, pk, *args, **kwargs):
        if not _can_change_remuneration(request.user):
            return HttpResponseForbidden('無修改勞務報酬單的權限')
        obj = get_object_or_404(ServiceRemuneration, pk=pk, is_deleted=False)
        slip_type = request.POST.get('slip_type')
        field = 'premium_payment_status' if slip_type == 'supplementary' else 'withholding_payment_status'

        current = getattr(obj, field)
        if current == ServiceRemuneration.PaymentSlipStatus.PENDING:
            setattr(obj, field, ServiceRemuneration.PaymentSlipStatus.MANUAL_PAID)
            msg = '已標記為已繳納（人工確認）'
        elif current == ServiceRemuneration.PaymentSlipStatus.MANUAL_PAID:
            setattr(obj, field, ServiceRemuneration.PaymentSlipStatus.PENDING)
            msg = '已取消人工繳納標記'
        else:
            messages.error(request, '此狀態不可人工標記（無須繳納或已有上傳憑證）')
            return _redirect_back(request)

        obj.save()
        messages.success(request, f'{obj.client.name}／{obj.recipient_name}：{msg}')
        return _redirect_back(request)
