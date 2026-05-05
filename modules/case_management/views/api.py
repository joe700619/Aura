"""案件管理輔助 API（內部用）"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from modules.bookkeeping.models import BookkeepingClient


User = get_user_model()


class BookkeepingClientLookupView(LoginRequiredMixin, View):
    """供案件建立表單做客戶搜尋與自動填入"""

    def get(self, request):
        if getattr(request.user, 'role', None) == 'EXTERNAL':
            return JsonResponse([], safe=False)

        q = request.GET.get('q', '').strip()
        qs = BookkeepingClient.objects.filter(is_deleted=False).select_related('bookkeeping_assistant__user')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(tax_id__icontains=q))
        qs = qs.order_by('name')[:30]

        data = []
        for c in qs:
            assistant_user_id = None
            assistant_name = ''
            if c.bookkeeping_assistant:
                assistant_name = c.bookkeeping_assistant.name
                if c.bookkeeping_assistant.user_id:
                    assistant_user_id = c.bookkeeping_assistant.user_id
            data.append({
                'id': c.pk,
                'name': c.name,
                'tax_id': c.tax_id or '',
                'contact_person': c.contact_person or '',
                'email': c.email or '',
                'mobile': c.mobile or c.phone or '',
                'assistant_name': assistant_name,
                'assistant_user_id': assistant_user_id,
            })
        return JsonResponse(data, safe=False)


class StaffUserLookupView(LoginRequiredMixin, View):
    """供案件表單做負責會計師（內部 user）搜尋"""

    def get(self, request):
        if getattr(request.user, 'role', None) == 'EXTERNAL':
            return JsonResponse([], safe=False)

        q = request.GET.get('q', '').strip()
        qs = User.objects.filter(is_active=True).exclude(role='EXTERNAL')
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
        qs = qs.order_by('first_name', 'username')[:30]

        data = [{
            'id': u.pk,
            'name': u.get_full_name() or u.username,
            'username': u.username,
            'email': u.email or '',
        } for u in qs]
        return JsonResponse(data, safe=False)
