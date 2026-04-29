import datetime
import json

from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin
from modules.bookkeeping.models import TaxFilingPeriod
from modules.bookkeeping.models.billing import ClientBill
from modules.bookkeeping.models.progress import BookkeepingPeriod


class DashboardView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client

        today = datetime.date.today()
        context['pending_vat_periods'] = TaxFilingPeriod.objects.filter(
            year_record__client=client,
            filing_status__in=['waiting', 'not_notified'],
            tax_deadline__isnull=False,
            tax_deadline__gte=today - datetime.timedelta(days=15),
            tax_deadline__lte=today + datetime.timedelta(days=30),
        ).order_by('tax_deadline')

        available_years = list(
            TaxFilingPeriod.objects.filter(year_record__client=client)
            .values_list('year_record__year', flat=True)
            .distinct()
            .order_by('-year_record__year')
        )
        default_year = datetime.datetime.now().year - 1911
        try:
            selected_year = int(self.request.GET.get('year', default_year))
        except (ValueError, TypeError):
            selected_year = default_year
        if not available_years:
            available_years = [default_year]
        if selected_year not in available_years:
            selected_year = available_years[0]
        context['available_years'] = available_years
        context['selected_year'] = selected_year

        periods_this_year = TaxFilingPeriod.objects.filter(
            year_record__client=client, year_record__year=selected_year
        )
        context['total_sales_this_year'] = sum(p.sales_amount for p in periods_this_year)
        context['total_payable_this_year'] = sum(p.payable_tax for p in periods_this_year)

        unpaid_bills = ClientBill.objects.filter(
            client=client, status__in=['issued', 'overdue']
        )
        context['unpaid_bills_count'] = unpaid_bills.count()
        context['unpaid_bills_amount'] = sum(b.total_amount for b in unpaid_bills)

        context['active_bookkeeping_periods'] = BookkeepingPeriod.objects.filter(
            year_record__client=client,
            account_status='in_progress'
        ).select_related('year_record').order_by('-year_record__year', '-period_start_month')

        all_tax_periods = list(reversed(list(
            TaxFilingPeriod.objects.filter(year_record__client=client)
            .select_related('year_record')
            .order_by('-year_record__year', '-period_start_month')[:12]
        )))
        context['chart_all_labels'] = json.dumps(
            [f"{p.year_record.year}/{p.period_start_month:02d}" for p in all_tax_periods]
        )
        context['chart_all_sales'] = json.dumps([float(p.sales_amount) for p in all_tax_periods])
        context['chart_all_input'] = json.dumps([float(p.input_amount) for p in all_tax_periods])

        from modules.administrative.models import ClientTaxEvent
        _today = datetime.date.today()
        active_events = ClientTaxEvent.objects.filter(
            is_active=True,
            deadline__gte=_today - datetime.timedelta(days=15),
        ).order_by('deadline')[:8]
        calendar_events = [
            {
                'label': e.title,
                'deadline': e.deadline,
                'is_urgent': e.is_urgent_on(_today),
            }
            for e in active_events
        ]
        context['tax_calendar'] = calendar_events
        context['tax_calendar_json'] = json.dumps([
            {'label': e['label'], 'deadline': e['deadline'].strftime('%Y-%m-%d'), 'is_urgent': e['is_urgent']}
            for e in calendar_events
        ])

        return context
