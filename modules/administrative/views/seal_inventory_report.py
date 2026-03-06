from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from ..models import SealProcurement, SealProcurementItem


class SealInventoryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'administrative/seal_procurement/seal_inventory_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')

        # Get all procurements that have transfer_to_inventory = True
        procurements = SealProcurement.objects.filter(transfer_to_inventory=True)
        if q:
            procurements = procurements.filter(
                company_name__icontains=q
            ) | SealProcurement.objects.filter(
                transfer_to_inventory=True,
                unified_business_no__icontains=q
            )

        # Group by company (unified_business_no)
        summary_data = []
        companies = procurements.values(
            'unified_business_no', 'company_name'
        ).distinct().order_by('company_name')

        grand_total = 0
        for company in companies:
            items = SealProcurementItem.objects.filter(
                procurement__transfer_to_inventory=True,
                procurement__unified_business_no=company['unified_business_no']
            ).select_related('procurement')

            if q:
                items = items.filter(
                    procurement__company_name__icontains=q
                ) | SealProcurementItem.objects.filter(
                    procurement__transfer_to_inventory=True,
                    procurement__unified_business_no=company['unified_business_no'],
                    procurement__unified_business_no__icontains=q
                )

            # Aggregate by seal type
            type_summary = items.values('seal_type').annotate(
                total_qty=Sum('quantity'),
                total_amount=Sum('subtotal')
            ).order_by('seal_type')

            # Build a flat dict: seal_type -> qty for easy template access
            type_qty = {code: 0 for code, _ in SealProcurementItem.SEAL_TYPE_CHOICES}
            for ts in type_summary:
                type_qty[ts['seal_type']] = ts['total_qty'] or 0

            # All individual items for the expanded detail view
            details = items.order_by('-procurement__created_at')

            company_total = sum(ts['total_amount'] or 0 for ts in type_summary)
            grand_total += company_total

            summary_data.append({
                'unified_business_no': company['unified_business_no'],
                'company_name': company['company_name'],
                'type_qty': type_qty,
                'total_amount': company_total,
                'details': details,
            })

        context['summary_data'] = summary_data
        context['grand_total'] = grand_total
        context['q'] = q
        context['seal_type_choices'] = dict(SealProcurementItem.SEAL_TYPE_CHOICES)
        return context
