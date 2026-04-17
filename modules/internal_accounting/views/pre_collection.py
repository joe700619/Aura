import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, DeleteView

from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, FilterMixin, PrevNextMixin
from ..forms import PreCollectionForm
from ..models import PreCollection

logger = logging.getLogger(__name__)


class PreCollectionListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = PreCollection
    template_name = 'pre_collection/list.html'
    context_object_name = 'pre_collections'
    paginate_by = 25
    search_fields = ['pre_collection_no', 'company_name', 'unified_business_no', 'transaction_no']
    filter_choices = {
        'UNMATCHED': {'status': PreCollection.Status.UNMATCHED},
        'MATCHED':   {'status': PreCollection.Status.MATCHED},
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '預收款項'
        context['model_name'] = 'internal_accounting:pre_collection'
        context['model_app_label'] = 'internal_accounting'
        context['create_button_label'] = '新增預收款項'
        context['count_all']       = context['filter_counts']['ALL']
        context['count_unmatched'] = context['filter_counts']['UNMATCHED']
        context['count_matched']   = context['filter_counts']['MATCHED']
        return context


class PreCollectionUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = PreCollection
    form_class = PreCollectionForm
    template_name = 'pre_collection/form.html'
    prev_next_order_field = 'date'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:pre_collection_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '預收款項明細'
        # Source progress object if available
        source = self.object.source_object
        context['source_object'] = source
        return context


class PreCollectionDeleteView(BusinessRequiredMixin, DeleteView):
    model = PreCollection
    template_name = 'pre_collection/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:pre_collection_list')


@login_required
def match_pre_collection_view(request, pk):
    """預收款項過帳：產生傳票草稿並標記為已核銷。"""
    from modules.internal_accounting.services import PreCollectionService

    pre_collection = get_object_or_404(PreCollection, pk=pk)

    if pre_collection.status == PreCollection.Status.MATCHED:
        messages.warning(request, '此預收款項已核銷，請勿重複操作。')
        return redirect('internal_accounting:pre_collection_edit', pk=pk)

    if request.method == 'POST':
        debit_code = request.POST.get('debit_code', '').strip()
        debit_name = request.POST.get('debit_name', '').strip()

        try:
            voucher = PreCollectionService.post_voucher(
                pre_collection=pre_collection,
                user=request.user,
                debit_code=debit_code or None,
                debit_name=debit_name or None,
            )
            from django.urls import reverse
            from django.http import HttpResponse
            voucher_url = reverse('internal_accounting:voucher_edit', kwargs={'pk': voucher.pk})
            back_url = reverse('internal_accounting:pre_collection_edit', kwargs={'pk': pk})
            return HttpResponse(
                f'<script>window.open("{voucher_url}","_blank");window.location.href="{back_url}";</script>'
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f'PreCollection post failed: {e}')
            messages.error(request, f'過帳失敗：{e}')
            return redirect('internal_accounting:pre_collection_edit', pk=pk)

    return redirect('internal_accounting:pre_collection_edit', pk=pk)
