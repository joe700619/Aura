import json
from collections import defaultdict

from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin


class ShareholderManagementView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/shareholders.html'

    def get_context_data(self, **kwargs):
        from modules.registration.models import ShareholderRegister

        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client

        register = ShareholderRegister.objects.filter(
            unified_business_no=client.tax_id
        ).prefetch_related('equity_transactions', 'directors').first()
        context['register'] = register

        if register:
            transactions = list(
                register.equity_transactions.all().order_by('transaction_date', 'created_at')
            )

            timeline_dict = defaultdict(list)
            for tx in transactions:
                timeline_dict[tx.transaction_date].append(tx)
            raw_timeline = sorted(timeline_dict.items(), key=lambda x: x[0], reverse=True)
            timeline = []
            for date, txs in raw_timeline:
                seen = list(dict.fromkeys(tx.get_transaction_reason_display() for tx in txs))
                timeline.append((date, txs, '、'.join(seen)))
            context['timeline'] = timeline

            all_tx = [
                {
                    'date': tx.transaction_date.strftime('%Y-%m-%d'),
                    'name': tx.shareholder_name,
                    'id': tx.shareholder_id_number,
                    'stype': tx.stock_type,
                    'slabel': tx.get_stock_type_display(),
                    'price': float(tx.unit_price),
                    'count': int(tx.share_count),
                    'amount': float(tx.total_amount),
                }
                for tx in transactions
            ]
            context['all_tx_json'] = json.dumps(all_tx, ensure_ascii=False)
            context['timeline_dates_json'] = json.dumps([
                d.strftime('%Y-%m-%d')
                for d in sorted(timeline_dict.keys(), reverse=True)
            ])

            context['equity_transactions'] = list(reversed(transactions))
            context['directors'] = list(register.directors.all())
        else:
            context['all_tx_json'] = '[]'
            context['timeline_dates_json'] = '[]'
            context['equity_transactions'] = []
            context['directors'] = []

        return context
