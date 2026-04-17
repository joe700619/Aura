from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.forms import inlineformset_factory
from collections import defaultdict
from core.mixins import BusinessRequiredMixin, ListActionMixin, PrevNextMixin, SoftDeleteMixin, FilterMixin, SearchMixin, SortMixin
from ..models import ShareholderRegister, DirectorSupervisor
from ..forms import ShareholderRegisterForm

# ── Director inline formset ──────────────────────────────────────────────────
DirectorFormSet = inlineformset_factory(
    ShareholderRegister,
    DirectorSupervisor,
    fields=['title', 'name', 'id_number', 'nationality', 'birth_date',
            'shares_held', 'entity_name', 'entity_no', 'order'],
    extra=0,
    can_delete=True,
)


class ShareholderRegisterListView(SortMixin, FilterMixin, SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    model = ShareholderRegister
    template_name = 'shareholder_register/list.html'
    context_object_name = 'registers'
    paginate_by = 25
    search_fields = ['company_name', 'unified_business_no']
    default_filter = 'UNCOMPLETED'
    filter_choices = {
        'UNCOMPLETED': {'completion_status': 'UNCOMPLETED'},
        'COMPLETED':   {'completion_status': 'COMPLETED'},
    }
    allowed_sort_fields = ['company_name', 'unified_business_no', 'service_status', 'completion_status']
    default_sort = ['company_name']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_all']         = context['filter_counts']['ALL']
        context['count_uncompleted'] = context['filter_counts']['UNCOMPLETED']
        context['count_completed']   = context['filter_counts']['COMPLETED']
        return context


class ShareholderRegisterCreateView(BusinessRequiredMixin, CreateView):
    model = ShareholderRegister
    form_class = ShareholderRegisterForm
    template_name = 'shareholder_register/form.html'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        return context


class ShareholderRegisterUpdateView(BusinessRequiredMixin, PrevNextMixin, UpdateView):
    model = ShareholderRegister
    form_class = ShareholderRegisterForm
    template_name = 'shareholder_register/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:shareholder_register_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        print("!!! DEBUG: ShareholderRegisterUpdateView EXECUTED !!!")
        context = super().get_context_data(**kwargs)
        transactions = self.object.equity_transactions.all().order_by('-transaction_date', '-created_at')
        context['equity_transactions'] = transactions
        context['action'] = 'update'

        # Timeline
        timeline_dict = defaultdict(list)
        for tx in transactions.order_by('transaction_date', 'created_at'):
            timeline_dict[tx.transaction_date].append(tx)
        raw_timeline = sorted(timeline_dict.items(), key=lambda x: x[0], reverse=True)
        timeline = []
        for date, txs in raw_timeline:
            seen = list(dict.fromkeys(tx.get_transaction_reason_display() for tx in txs))
            unique_reasons = '、'.join(seen)
            timeline.append((date, txs, unique_reasons))
        context['timeline'] = timeline

        # Pre-serialize to JSON for Alpine.js
        import json
        all_tx = []
        for tx in transactions.order_by('transaction_date', 'created_at'):
            all_tx.append({
                'date': tx.transaction_date.strftime('%Y-%m-%d'),
                'name': tx.shareholder_name,
                'id': tx.shareholder_id_number,
                'stype': tx.stock_type,
                'slabel': tx.get_stock_type_display(),
                'price': float(tx.unit_price),
                'count': int(tx.share_count),
                'amount': float(tx.total_amount),
            })
        context['all_tx_json'] = json.dumps(all_tx, ensure_ascii=False)

        timeline_dates = [
            d.strftime('%Y-%m-%d')
            for d in sorted(timeline_dict.keys(), reverse=True)
        ]
        context['timeline_dates_json'] = json.dumps(timeline_dates)

        # Director title choices for JS
        title_choices = [[c[0], str(c[1])] for c in DirectorSupervisor.Title.choices]
        context['director_title_choices_json'] = json.dumps(title_choices, ensure_ascii=False)

        # Director formset
        if self.request.POST:
            context['director_formset'] = DirectorFormSet(self.request.POST, instance=self.object)
        else:
            context['director_formset'] = DirectorFormSet(instance=self.object)

        # 編修紀錄
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        director_formset = context['director_formset']
        if director_formset.is_valid():
            self.object = form.save()
            director_formset.instance = self.object
            director_formset.save()
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class ShareholderRegisterDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = ShareholderRegister
    template_name = 'shareholder_register/confirm_delete.html'
    success_url = reverse_lazy('registration:shareholder_register_list')
