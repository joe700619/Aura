"""記帳交接儀表板（組長保險絲）。

並排兩欄：①待指派助理 ②已指派、待首次聯繫。提醒會被無視，但卡住的案
紅著掛在這頁上不會——「看得見勝過自動化」。顯示「全部」收件匣項目（非只逾期），
逾期者（超過 SLA 門檻）標紅。為監督用途，不套用員工資料隔離，顯示全部。
"""
from django.utils import timezone
from django.views.generic import TemplateView

from core.mixins import BusinessRequiredMixin

from ..models import BookkeepingClient
from ..services.onboarding_sla import (
    ASSIGN_DAYS, CONTACT_DAYS, ESCALATE_DAYS, _onboarding_base_qs,
)


class OnboardingDashboardView(BusinessRequiredMixin, TemplateView):
    template_name = 'bookkeeping/onboarding_dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        base = _onboarding_base_qs()

        unassigned = []
        for c in base.filter(
            bookkeeping_assistant__isnull=True
        ).order_by('created_at'):
            days = (today - c.created_at.date()).days
            unassigned.append({
                'client': c,
                'days': days,
                'overdue': days >= ASSIGN_DAYS,
                'escalated': days >= ESCALATE_DAYS,
            })

        uncontacted = []
        for c in base.filter(
            bookkeeping_assistant__isnull=False,
            contact_date__isnull=True,
            assigned_at__isnull=False,
        ).select_related('bookkeeping_assistant').order_by('assigned_at'):
            days = (today - c.assigned_at).days
            uncontacted.append({
                'client': c,
                'days': days,
                'overdue': days >= CONTACT_DAYS,
                'escalated': days >= ESCALATE_DAYS,
            })

        context.update({
            'unassigned': unassigned,
            'uncontacted': uncontacted,
            'unassigned_count': len(unassigned),
            'uncontacted_count': len(uncontacted),
            'assign_days': ASSIGN_DAYS,
            'contact_days': CONTACT_DAYS,
        })
        return context
