from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_POST

from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, PrevNextMixin, FilterMixin
from ..models import Collection, Receivable
from ..forms import CollectionForm
from ..services import AccountingService


class CollectionListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = Collection
    template_name = 'collection/list.html'
    context_object_name = 'collections'
    paginate_by = 25
    search_fields = ['collection_no', 'receivable__company_name']
    filter_choices = {
        'POSTED':   {'is_posted': True},
        'UNPOSTED': {'is_posted': False},
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '收款管理'
        context['model_name'] = 'internal_accounting:collection'
        context['model_app_label'] = 'internal_accounting'
        context['create_button_label'] = '新增收款紀錄'
        context['count_all']      = context['filter_counts']['ALL']
        context['count_posted']   = context['filter_counts']['POSTED']
        context['count_unposted'] = context['filter_counts']['UNPOSTED']
        return context


class CollectionCreateView(BusinessRequiredMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = 'collection/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:collection_edit', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        receivable_id = self.request.GET.get('receivable_id')
        if receivable_id:
            receivable = get_object_or_404(Receivable, pk=receivable_id)
            initial['receivable'] = receivable

            for field in ['amount', 'tax', 'fee', 'allowance']:
                val = self.request.GET.get(field)
                if val:
                    try:
                        initial[field] = int(float(val))
                    except (ValueError, TypeError):
                        pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增收款紀錄'
        context['action'] = 'create'
        context['cancel_url'] = reverse_lazy('internal_accounting:collection_list')
        receivable_id = self.request.GET.get('receivable_id')
        if receivable_id:
            context['prefilled_receivable'] = get_object_or_404(Receivable, pk=receivable_id)
        return context

    def form_valid(self, form):
        messages.success(self.request, "收款紀錄已建立")
        return super().form_valid(form)


class CollectionUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = Collection
    form_class = CollectionForm
    template_name = 'collection/form.html'

    def get_success_url(self):
        return reverse_lazy('internal_accounting:collection_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯收款紀錄: {self.object.collection_no}'
        context['action'] = 'update'
        context['cancel_url'] = reverse_lazy('internal_accounting:collection_list')

        if self.object and hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or "資料變更",
                })
            context['history'] = history_list

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 已過帳：鎖定所有欄位
        if self.object and self.object.is_posted:
            for field in form.fields.values():
                field.widget.attrs['disabled'] = True
                field.widget.attrs['readonly'] = True
        return form

    def form_valid(self, form):
        # 已過帳的收款不允許修改
        if self.object.is_posted:
            messages.error(self.request, "此筆收款已過帳，不允許修改。")
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, "收款紀錄已更新")
        return super().form_valid(form)


class CollectionDeleteView(BusinessRequiredMixin, DeleteView):
    model = Collection
    template_name = 'collection/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:collection_list')

    def form_valid(self, _form):
        self.object = self.get_object()

        # 已過帳：連動作廢傳票
        if self.object.is_posted and self.object.voucher:
            from ..models.voucher import Voucher
            self.object.voucher.status = Voucher.Status.DRAFT
            self.object.voucher.description = f"[已作廢] {self.object.voucher.description}"
            self.object.voucher.save(update_fields=['status', 'description'])

        self.object.is_deleted = True
        self.object.save(update_fields=['is_deleted', 'updated_at'])
        messages.success(self.request, f"「{self.object}」已成功刪除（移至資源回收桶）。")
        return HttpResponseRedirect(self.success_url)


@login_required
@require_POST
def post_collection_view(request, pk):
    collection = get_object_or_404(Collection, pk=pk, is_deleted=False)
    try:
        voucher = AccountingService.post_collection(collection, request.user)
        messages.success(request, f"收款已過帳，傳票編號：{voucher.voucher_no}")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"過帳失敗：{e}")
    return HttpResponseRedirect(
        reverse_lazy('internal_accounting:collection_edit', kwargs={'pk': pk})
    )


def search_receivables(request):
    query = request.GET.get('q', '')
    receivables = Receivable.objects.filter(
        Q(company_name__icontains=query) |
        Q(unified_business_no__icontains=query) |
        Q(receivable_no__icontains=query)
    ).order_by('company_name')[:20]

    return render(request, 'internal_accounting/partials/receivable_search_results.html', {
        'receivables': receivables
    })


@login_required
def search_receivables_json(request):
    """JSON 版應收帳款搜尋，供預收款項核銷 Modal 使用。"""
    query = request.GET.get('q', '')
    receivables = Receivable.objects.filter(
        Q(company_name__icontains=query) |
        Q(unified_business_no__icontains=query) |
        Q(receivable_no__icontains=query)
    ).order_by('company_name')[:20]

    data = [
        {
            'id': r.pk,
            'receivable_no': r.receivable_no or '',
            'company_name': r.company_name,
            'outstanding': str(r.outstanding_balance),
        }
        for r in receivables
    ]
    return JsonResponse({'results': data})
