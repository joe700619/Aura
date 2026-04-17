from django.views.generic import TemplateView
from core.mixins import BusinessRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Sum
from ..models import SealProcurement, SealProcurementItem

PAGINATE_BY = 25


class SealInventoryReportView(BusinessRequiredMixin, TemplateView):
    template_name = 'administrative/seal_procurement/seal_inventory_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        page_number = self.request.GET.get('page', 1)

        procurements = SealProcurement.objects.filter(transfer_to_inventory=True)
        if q:
            procurements = procurements.filter(
                company_name__icontains=q
            ) | SealProcurement.objects.filter(
                transfer_to_inventory=True,
                unified_business_no__icontains=q
            )

        companies = procurements.values(
            'unified_business_no', 'company_name'
        ).distinct().order_by('company_name')

        # Build summary for all companies (lightweight — no details yet)
        all_summary = []
        grand_total = 0
        for company in companies:
            items_qs = SealProcurementItem.objects.filter(
                procurement__transfer_to_inventory=True,
                procurement__unified_business_no=company['unified_business_no']
            )
            type_summary = items_qs.values('seal_type').annotate(
                total_qty=Sum('quantity'),
                total_amount=Sum('subtotal')
            )
            type_qty = {code: 0 for code, _ in SealProcurementItem.SEAL_TYPE_CHOICES}
            company_total = 0
            for ts in type_summary:
                type_qty[ts['seal_type']] = ts['total_qty'] or 0
                company_total += ts['total_amount'] or 0
            grand_total += company_total
            all_summary.append({
                'unified_business_no': company['unified_business_no'],
                'company_name': company['company_name'],
                'type_qty': type_qty,
                'total_amount': company_total,
            })

        # Paginate the summary list
        paginator = Paginator(all_summary, PAGINATE_BY)
        page_obj = paginator.get_page(page_number)

        # Attach details only for the current page rows (avoids loading all rows)
        for row in page_obj:
            row['details'] = SealProcurementItem.objects.filter(
                procurement__transfer_to_inventory=True,
                procurement__unified_business_no=row['unified_business_no']
            ).select_related('procurement').order_by('-procurement__created_at')

        context['page_obj'] = page_obj
        context['paginator'] = paginator
        context['is_paginated'] = paginator.num_pages > 1
        context['summary_data'] = page_obj          # template iterates this
        context['grand_total'] = grand_total        # grand total across ALL pages
        context['q'] = q
        context['seal_type_choices'] = dict(SealProcurementItem.SEAL_TYPE_CHOICES)
        return context
