"""案件分析 views — 按 client portal 公司統計"""
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Max, Q
from django.views.generic import TemplateView

from .internal import StaffRequiredMixin
from ..models import Case


def _get_bk_content_type():
    from modules.bookkeeping.models import BookkeepingClient
    return ContentType.objects.get_for_model(BookkeepingClient)


class ClientCaseAnalyticsView(StaffRequiredMixin, TemplateView):
    template_name = 'case_management/internal/client_analytics.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ct = _get_bk_content_type()
        portal_cases = Case.objects.filter(
            source=Case.Source.CLIENT_PORTAL,
            client_content_type=ct,
            is_deleted=False,
        )

        # 按公司彙整：total、各 category 數、最新案件時間
        category_fields = {c[0]: Count('id', filter=Q(category=c[0])) for c in Case.Category.choices}
        company_stats = (
            portal_cases
            .values('client_object_id')
            .annotate(
                total=Count('id'),
                last_case_at=Max('created_at'),
                **category_fields,
            )
            .order_by('-total')
        )

        # 批次取得 BookkeepingClient 資料（避免 N+1）
        from modules.bookkeeping.models import BookkeepingClient
        client_ids = [r['client_object_id'] for r in company_stats]
        clients_map = {
            c.pk: c
            for c in BookkeepingClient.objects.filter(pk__in=client_ids).select_related('customer')
        }

        # 組合最終資料
        category_choices = Case.Category.choices
        rows = []
        for stat in company_stats:
            client = clients_map.get(stat['client_object_id'])
            if not client:
                continue
            breakdown = [
                {'label': label, 'value': stat.get(code, 0), 'code': code}
                for code, label in category_choices
            ]
            top_category = max(breakdown, key=lambda x: x['value'], default=None)
            rows.append({
                'client': client,
                'total': stat['total'],
                'last_case_at': stat['last_case_at'],
                'breakdown': breakdown,
                'top_category': top_category if top_category and top_category['value'] > 0 else None,
            })

        ctx['rows'] = rows
        ctx['category_choices'] = Case.Category.choices
        ctx['total_companies'] = len(rows)
        ctx['total_cases'] = portal_cases.count()
        return ctx
