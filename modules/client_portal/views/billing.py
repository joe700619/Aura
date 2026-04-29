import random
import urllib.parse
from datetime import date as _date

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin
from modules.internal_accounting.models.receivable import Receivable

_SORT_FIELDS = {
    'no':      lambda r: (r.receivable_no or ''),
    'date':    lambda r: (r.date or _date.min),
    'balance': lambda r: r.outstanding_balance,
    'status':  lambda r: r.status,
}
_DEFAULT_DIR = {'balance': 'desc'}
_PAGE_SIZE = 25


class BillingView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/billing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile

        all_receivables = []
        if client.tax_id:
            all_receivables = list(
                Receivable.objects.filter(
                    unified_business_no=client.tax_id,
                    is_deleted=False,
                ).prefetch_related('collections').order_by('-date', '-created_at')
            )

        # ── 狀態篩選 ──
        status_filter = self.request.GET.get('status', 'outstanding')
        if status_filter == 'all':
            bills = all_receivables[:]
        else:
            status_filter = 'outstanding'
            bills = [r for r in all_receivables if r.outstanding_balance > 0]

        # ── 排序 ──
        sort = self.request.GET.get('sort', 'date')
        if sort not in _SORT_FIELDS:
            sort = 'date'
        direction = self.request.GET.get('dir', 'desc')
        if direction not in ('asc', 'desc'):
            direction = 'desc'
        bills.sort(key=_SORT_FIELDS[sort], reverse=(direction == 'desc'))

        # ── 分頁 ──
        paginator = Paginator(bills, _PAGE_SIZE)
        page_number = self.request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        # 分頁連結的基底參數（保留 status / sort / dir）
        base_params = f"status={status_filter}&sort={sort}&dir={direction}"

        # ── 欄位排序連結（保留 status，重置到第 1 頁） ──
        def _sort_url(col):
            if sort == col:
                new_dir = 'asc' if direction == 'desc' else 'desc'
            else:
                new_dir = _DEFAULT_DIR.get(col, 'asc')
            return f"?status={status_filter}&sort={col}&dir={new_dir}"

        context['page_obj'] = page_obj
        context['status_filter'] = status_filter
        context['outstanding_count'] = sum(1 for r in all_receivables if r.outstanding_balance > 0)
        context['all_count'] = len(all_receivables)
        context['sort'] = sort
        context['sort_dir'] = direction
        context['sort_urls'] = {col: _sort_url(col) for col in _SORT_FIELDS}
        context['base_params'] = base_params
        return context


class GeneratePaymentLinkView(ClientRequiredMixin, View):
    def post(self, request, pk):
        from modules.payment.models import PaymentTransaction

        client = request.user.bookkeeping_client_profile
        receivable = get_object_or_404(Receivable, pk=pk, is_deleted=False)

        if not client.tax_id or receivable.unified_business_no != client.tax_id:
            return JsonResponse({'error': '無權限存取此帳單'}, status=403)

        outstanding = int(receivable.outstanding_balance)
        if outstanding <= 0:
            return JsonResponse({'error': '帳款已結清，無需付款'}, status=400)

        random_suffix = f"{random.randint(0, 9999):04d}"
        base_no = (receivable.receivable_no or str(receivable.pk)).replace('-', '')
        merchant_trade_no = f"{base_no}{random_suffix}"[:20]

        PaymentTransaction.objects.create(
            merchant_trade_no=merchant_trade_no,
            total_amount=outstanding,
            trade_desc=f"應收帳款 {receivable.receivable_no or receivable.pk}",
            item_name=f"服務費用 ({receivable.company_name})"[:200],
            payment_type=PaymentTransaction.PaymentType.ECPAY,
            related_app='internal_accounting',
            related_model='Receivable',
            related_id=str(receivable.pk),
        )

        base_url = f"{request.scheme}://{request.get_host()}"
        pay_url = f"{base_url}/payment/bill/{merchant_trade_no}/"
        return JsonResponse({'url': pay_url})


class DownloadBillPdfView(ClientRequiredMixin, View):
    def get(self, request, pk):
        from core.models import DocumentTemplate
        from core.services.document import DocumentService

        client = request.user.bookkeeping_client_profile
        receivable = get_object_or_404(Receivable, pk=pk, is_deleted=False)

        if not client.tax_id or receivable.unified_business_no != client.tax_id:
            return HttpResponse('無權限存取此帳單', status=403)

        content_type = ContentType.objects.get_for_model(Receivable)
        template = DocumentTemplate.objects.filter(model_content_type=content_type).first()
        if not template:
            return HttpResponse('尚未設定帳單範本，請聯絡會計師事務所', status=404)

        try:
            buffer = DocumentService.render_template(template, receivable, output_format='pdf')
        except Exception as e:
            return HttpResponse(f'PDF 產生失敗：{e}', status=500)

        filename = urllib.parse.quote(f"帳單_{receivable.receivable_no or pk}.pdf")
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
