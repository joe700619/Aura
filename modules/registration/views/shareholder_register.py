from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.forms import inlineformset_factory
from collections import defaultdict
from core.mixins import ListActionMixin, PrevNextMixin
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


class ShareholderRegisterListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = ShareholderRegister
    template_name = 'shareholder_register/list.html'
    context_object_name = 'registers'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        status = self.request.GET.get('status', 'UNCOMPLETED')
        if status != 'ALL':
            queryset = queryset.filter(completion_status=status)

        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(company_name__icontains=q) |
                Q(unified_business_no__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', 'UNCOMPLETED')
        return context


class ShareholderRegisterCreateView(LoginRequiredMixin, CreateView):
    model = ShareholderRegister
    form_class = ShareholderRegisterForm
    template_name = 'shareholder_register/form_v3.html'
    success_url = reverse_lazy('registration:shareholder_register_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        return context


class ShareholderRegisterUpdateView(LoginRequiredMixin, PrevNextMixin, UpdateView):
    model = ShareholderRegister
    form_class = ShareholderRegisterForm
    template_name = 'shareholder_register/form_v3.html'
    success_url = reverse_lazy('registration:shareholder_register_list')

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


class ShareholderRegisterDeleteView(LoginRequiredMixin, DeleteView):
    model = ShareholderRegister
    template_name = 'shareholder_register/confirm_delete.html'
    success_url = reverse_lazy('registration:shareholder_register_list')
