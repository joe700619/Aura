from datetime import date
from core.mixins import BusinessRequiredMixin
from django.db.models import Sum, Q
from django.views.generic import TemplateView

from ..models.fixed_asset import FixedAsset
from ..models.voucher import Voucher
from ..models.voucher_detail import VoucherDetail


class FixedAssetReportView(BusinessRequiredMixin, TemplateView):
    template_name = 'fixed_asset/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '固定資產期末明細表'
        context['today'] = date.today()

        query_date_str = self.request.GET.get('date', '')
        query_date = None

        if query_date_str:
            try:
                query_date = date.fromisoformat(query_date_str)
            except ValueError:
                pass

        context['query_date'] = query_date

        if query_date:
            context['rows'] = self._build_rows(query_date)

        return context

    def _build_rows(self, query_date):
        # All assets purchased on or before query_date
        assets = FixedAsset.objects.filter(
            purchase_date__lte=query_date,
            is_deleted=False
        ).order_by('purchase_date', 'asset_no')

        # Sum depreciation credits from posted DEPRECIATION vouchers up to query_date,
        # grouped by asset_no (stored in VoucherDetail.project)
        depreciation_qs = (
            VoucherDetail.objects
            .filter(
                voucher__source=Voucher.Source.DEPRECIATION,
                voucher__status=Voucher.Status.POSTED,
                voucher__date__lte=query_date,
            )
            .values('project')
            .annotate(total=Sum('credit'))
        )
        dep_map = {row['project']: row['total'] for row in depreciation_qs}

        rows = []
        total_cost = 0
        total_accum = 0
        total_net = 0

        for asset in assets:
            accum = dep_map.get(asset.asset_no, 0)
            net = asset.cost - accum
            salvage = asset.salvage_value
            is_full = net <= salvage

            rows.append({
                'asset': asset,
                'accumulated_as_of': accum,
                'net_value_as_of': net,
                'is_fully_depreciated': is_full,
            })
            total_cost += asset.cost
            total_accum += accum
            total_net += net

        return {
            'items': rows,
            'total_cost': total_cost,
            'total_accum': total_accum,
            'total_net': total_net,
        }
