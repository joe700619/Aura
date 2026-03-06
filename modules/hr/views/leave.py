from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from core.mixins import CopyMixin, PrevNextMixin, ListActionMixin
from ..models import LeaveType, LeaveBalance, LeaveRequest
from ..forms import LeaveTypeForm, LeaveBalanceForm, LeaveRequestForm


# ==================== LeaveType ====================

class LeaveTypeListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = LeaveType
    template_name = 'leave_type/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增假別'

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '假別設定'
        context['custom_create_url'] = reverse_lazy('hr:leave_type_create')
        return context


class LeaveTypeCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'leave_type/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:leave_type_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增假別'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '假別已建立。')
        return redirect(self.get_success_url())


class LeaveTypeUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'leave_type/form.html'
    prev_next_order_field = 'sort_order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯假別 - {self.object.name}'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '假別已更新。')
        return redirect('hr:leave_type_update', pk=self.object.pk)


class LeaveTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = LeaveType
    success_url = reverse_lazy('hr:leave_type_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# ==================== LeaveBalance ====================

class LeaveBalanceListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = LeaveBalance
    template_name = 'leave_balance/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增餘額'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee', 'leave_type')
        year = self.request.GET.get('year')
        q = self.request.GET.get('q', '')
        if year:
            qs = qs.filter(year=year)
        if q:
            qs = qs.filter(employee__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '假期餘額'
        context['custom_create_url'] = reverse_lazy('hr:leave_balance_create')
        context['q'] = self.request.GET.get('q', '')
        context['selected_year'] = self.request.GET.get('year', '')
        context['years'] = sorted(
            LeaveBalance.objects.filter(is_deleted=False)
            .values_list('year', flat=True).distinct(),
            reverse=True,
        )
        return context


class LeaveBalanceCreateView(LoginRequiredMixin, CreateView):
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'leave_balance/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:leave_balance_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增假期餘額'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '假期餘額已建立。')
        return redirect(self.get_success_url())


class LeaveBalanceUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'leave_balance/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯餘額 - {self.object.employee.name} / {self.object.leave_type.name}'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '假期餘額已更新。')
        return redirect('hr:leave_balance_update', pk=self.object.pk)


class LeaveBalanceDeleteView(LoginRequiredMixin, DeleteView):
    model = LeaveBalance
    success_url = reverse_lazy('hr:leave_balance_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


class RecalculateLeaveView(LoginRequiredMixin, View):
    """重算所有在職員工的特休/病假餘額"""

    def post(self, request):
        from ..services.leave_calculator import recalculate_leave_balances
        results = recalculate_leave_balances(dry_run=False)
        created_count = sum(1 for r in results if r['action'] == 'created')
        total_count = len(results)
        messages.success(
            request,
            f'重算完成！共處理 {total_count} 筆，新建 {created_count} 筆。'
        )
        return redirect('hr:leave_balance_list')


# ==================== LeaveRequest ====================

class LeaveRequestListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'leave_request/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增請假'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee', 'leave_type')
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status')
        if q:
            qs = qs.filter(employee__name__icontains=q)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '請假管理'
        context['custom_create_url'] = reverse_lazy('hr:leave_request_create')
        context['q'] = self.request.GET.get('q', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leave_request/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:leave_request_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增請假單'
        return context

    def form_valid(self, form):
        self.object = form.save()
        
        # Deduct from balance based on the active period covering the start date
        start_date = self.object.start_datetime.date()
        balance = LeaveBalance.objects.filter(
            employee=self.object.employee,
            leave_type=self.object.leave_type,
            period_start__lte=start_date,
            period_end__gt=start_date,
        ).first()

        if not balance:
            # Fallback for leaves that might not have strict periods generated yet
            balance, _ = LeaveBalance.objects.get_or_create(
                employee=self.object.employee,
                leave_type=self.object.leave_type,
                year=self.object.start_datetime.year,
                defaults={'entitled_hours': 0},
            )

        balance.used_hours += self.object.total_hours
        balance.save(update_fields=['used_hours'])
        messages.success(self.request, '請假單已建立。')
        return redirect(self.get_success_url())


class LeaveRequestUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leave_request/form.html'
    prev_next_order_field = '-start_datetime'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯請假單 - {self.object.employee.name}'

        # 添加核准相關 context
        approval_request = self.object.get_approval_request()
        context['approval_request'] = approval_request
        if approval_request:
            context['can_approve'] = self.object.can_user_approve(self.request.user)
        else:
            context['can_approve'] = False

        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '請假單已更新。')
        return redirect('hr:leave_request_update', pk=self.object.pk)


class LeaveRequestDeleteView(LoginRequiredMixin, DeleteView):
    """Cancel (soft delete) a leave request and rollback balance"""
    model = LeaveRequest
    success_url = reverse_lazy('hr:leave_request_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.cancel()  # This handles status + balance rollback
        messages.success(request, '請假單已取消，餘額已回沖。')
        return redirect(self.success_url)


# ========== Leave Request Approval Action Views ==========

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from modules.workflow.services import (
    initiate_approval,
    submit_for_approval,
    approve as workflow_approve,
    reject as workflow_reject,
    return_for_revision,
    cancel_approval,
    get_effective_approver,
)


@login_required
def leave_request_submit_approval(request, pk):
    """送出請假單核准"""
    leave_req = get_object_or_404(LeaveRequest, pk=pk)

    if request.method == 'POST':
        try:
            approval_request = leave_req.get_approval_request()
            if not approval_request:
                approval_request = initiate_approval(
                    obj=leave_req,
                    workflow_code='leave_request',
                    requester=request.user,
                )
            submit_for_approval(approval_request, comments='')
            messages.success(request, f'{leave_req.employee.name} 的請假單已送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')

    return redirect('hr:leave_request_update', pk=pk)


@login_required
def leave_request_approve(request, pk):
    """核准請假單"""
    leave_req = get_object_or_404(LeaveRequest, pk=pk)

    if request.method == 'POST':
        approval_request = leave_req.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:leave_request_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            workflow_approve(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            # 核准通過後更新請假單狀態
            if approval_request.status == 'APPROVED':
                leave_req.status = 'approved'
                leave_req.approved_by = request.user
                leave_req.save(update_fields=['status', 'approved_by'])
            messages.success(request, '請假單已核准。')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')

    return redirect('hr:leave_request_update', pk=pk)


@login_required
def leave_request_reject(request, pk):
    """拒絕請假單"""
    leave_req = get_object_or_404(LeaveRequest, pk=pk)

    if request.method == 'POST':
        approval_request = leave_req.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:leave_request_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            workflow_reject(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            leave_req.status = 'rejected'
            leave_req.save(update_fields=['status'])
            messages.success(request, '請假單已駁回。')
        except Exception as e:
            messages.error(request, f'駁回失敗：{str(e)}')

    return redirect('hr:leave_request_update', pk=pk)


@login_required
def leave_request_return(request, pk):
    """退回請假單"""
    leave_req = get_object_or_404(LeaveRequest, pk=pk)

    if request.method == 'POST':
        approval_request = leave_req.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:leave_request_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            return_for_revision(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            messages.success(request, '請假單已退回申請人修正。')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')

    return redirect('hr:leave_request_update', pk=pk)


@login_required
def leave_request_cancel_approval(request, pk):
    """撤回請假單核准"""
    leave_req = get_object_or_404(LeaveRequest, pk=pk)

    if request.method == 'POST':
        approval_request = leave_req.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:leave_request_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            cancel_approval(approval_request, requester=request.user, comments=comments)
            messages.success(request, '請假單核准已撤回。')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')

    return redirect('hr:leave_request_update', pk=pk)
