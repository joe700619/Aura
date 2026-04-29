from datetime import date
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import BookkeepingPeriod, BookkeepingYear

_FULL_ACCESS_GROUPS = ['CPA', 'management', 'Admin']


class ProgressSummaryAPIView(LoginRequiredMixin, View):
    """API: Dashboard 記帳案件進度圓餅圖資料

    GET /bookkeeping/api/progress-summary/?year=115&month=4
    回傳 JSON：total / completed / in_progress / waiting_docs / not_started /
              clients / available_years / available_months / is_full_access
    """

    def get(self, request):
        today = date.today()
        roc_today = today.year - 1911

        try:
            year  = int(request.GET.get('year',  roc_today))
            month = int(request.GET.get('month', today.month))
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid parameters'}, status=400)

        user = request.user
        is_full_access = (
            user.is_superuser
            or user.groups.filter(name__in=_FULL_ACCESS_GROUPS).exists()
        )
        employee = getattr(user, 'employee_profile', None)

        # ── 期間資料 ──────────────────────────────────────────────────
        qs = BookkeepingPeriod.objects.filter(
            year_record__year=year,
            period_start_month=month,
        ).select_related(
            'year_record__client',
            'year_record__client__bookkeeping_assistant',
        )

        if not is_full_access:
            if not employee:
                qs = qs.none()
            else:
                qs = qs.filter(year_record__client__bookkeeping_assistant=employee)

        # ── 各狀態計數 ────────────────────────────────────────────────
        S = BookkeepingPeriod.AccountStatus
        completed    = qs.filter(account_status=S.COMPLETED).count()
        in_progress  = qs.filter(account_status=S.IN_PROGRESS).count()
        waiting_docs = qs.filter(account_status=S.WAITING_DOCS).count()
        not_started  = qs.filter(account_status=S.NOT_STARTED).count()
        total        = completed + in_progress + waiting_docs + not_started

        # ── 客戶明細 ──────────────────────────────────────────────────
        clients = []
        for period in qs.order_by('account_status', 'year_record__client__name'):
            assistant = period.year_record.client.bookkeeping_assistant
            clients.append({
                'name':           period.year_record.client.name,
                'tax_id':         period.year_record.client.tax_id or '',
                'status':         period.account_status,
                'status_display': period.get_account_status_display(),
                'assistant':      assistant.name if assistant else '',
            })

        # ── 可選年度 ──────────────────────────────────────────────────
        year_qs = BookkeepingYear.objects.all()
        if not is_full_access:
            year_qs = (
                year_qs.filter(client__bookkeeping_assistant=employee)
                if employee else year_qs.none()
            )
        available_years = sorted(
            set(year_qs.values_list('year', flat=True)),
            reverse=True,
        )
        if not available_years:
            available_years = [roc_today]

        # ── 可選月份（依選定年度） ─────────────────────────────────────
        month_qs = BookkeepingPeriod.objects.filter(year_record__year=year)
        if not is_full_access:
            month_qs = (
                month_qs.filter(year_record__client__bookkeeping_assistant=employee)
                if employee else month_qs.none()
            )
        available_months = sorted(
            set(month_qs.values_list('period_start_month', flat=True))
        )
        if not available_months:
            available_months = list(range(1, 13))

        return JsonResponse({
            'year':             year,
            'month':            month,
            'total':            total,
            'completed':        completed,
            'in_progress':      in_progress,
            'waiting_docs':     waiting_docs,
            'not_started':      not_started,
            'clients':          clients,
            'available_years':  available_years,
            'available_months': available_months,
            'is_full_access':   is_full_access,
        })
