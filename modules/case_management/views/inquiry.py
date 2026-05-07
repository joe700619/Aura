"""對外網站諮詢預約（潛在客戶）— 內部後台 views。"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, View

from ..models import Inquiry

User = get_user_model()


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, 'role', None) == 'EXTERNAL':
            return redirect('client_portal:dashboard')
        return super().dispatch(request, *args, **kwargs)


class InquiryListView(StaffRequiredMixin, ListView):
    model = Inquiry
    template_name = 'case_management/internal/inquiry_list.html'
    context_object_name = 'inquiries'
    paginate_by = 25

    def get_queryset(self):
        qs = Inquiry.objects.select_related('handled_by').order_by('-created_at')
        # 預設只顯示「待處理」；明確傳 ?status= 才顯示全部
        if 'status' in self.request.GET:
            status = self.request.GET['status']
        else:
            status = Inquiry.Status.NEW
        if status:
            qs = qs.filter(status=status)
        self._effective_status = status
        owner = self.request.GET.get('owner')
        if owner == 'me':
            qs = qs.filter(handled_by=self.request.user)
        elif owner == 'unassigned':
            qs = qs.filter(handled_by__isnull=True)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
                | Q(company__icontains=q) | Q(message__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Inquiry.Status.choices
        ctx['source_choices'] = Inquiry.Source.choices
        ctx['active_status'] = getattr(self, '_effective_status', '')
        ctx['active_owner'] = self.request.GET.get('owner', '')
        ctx['search_q'] = self.request.GET.get('q', '')
        # 概要計數
        all_inq = Inquiry.objects.values('status').annotate(c=Count('id'))
        ctx['counts'] = {row['status']: row['c'] for row in all_inq}
        ctx['counts']['total'] = sum(ctx['counts'].values())
        return ctx


class InquiryDetailView(StaffRequiredMixin, DetailView):
    model = Inquiry
    template_name = 'case_management/internal/inquiry_detail.html'
    context_object_name = 'inquiry'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Inquiry.Status.choices
        ctx['staff_users'] = User.objects.filter(is_active=True).exclude(role='EXTERNAL').order_by('username')
        return ctx


class InquiryUpdateView(StaffRequiredMixin, View):
    """單一端點：更新狀態 / 負責人 / 內部備註。"""

    def post(self, request, pk):
        inq = get_object_or_404(Inquiry, pk=pk)

        if 'status' in request.POST:
            new_status = request.POST.get('status')
            if new_status in dict(Inquiry.Status.choices):
                inq.status = new_status

        if 'handled_by' in request.POST:
            uid = request.POST.get('handled_by') or ''
            if uid == '':
                inq.handled_by = None
            else:
                try:
                    inq.handled_by = User.objects.get(pk=int(uid))
                except (User.DoesNotExist, ValueError):
                    pass

        if 'note' in request.POST:
            inq.note = request.POST.get('note', '')[:5000]

        inq.save()
        messages.success(request, '已更新諮詢資料')
        return redirect(reverse('case_management:inquiry_detail', kwargs={'pk': inq.pk}))


class InquiryClaimView(StaffRequiredMixin, View):
    """快速把諮詢指派給自己。"""

    def post(self, request, pk):
        inq = get_object_or_404(Inquiry, pk=pk)
        inq.handled_by = request.user
        if inq.status == Inquiry.Status.NEW:
            inq.status = Inquiry.Status.CONTACTED
        inq.save()
        messages.success(request, f'已認領「{inq.name}」的諮詢')
        return redirect(reverse('case_management:inquiry_detail', kwargs={'pk': inq.pk}))
