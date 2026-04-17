from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from core.mixins import HRRequiredMixin, OwnEmployeeDataMixin, CopyMixin, PrevNextMixin, ListActionMixin, SearchMixin, SortMixin, SoftDeleteMixin, _HR_ATTENDANCE_ACCESS_GROUPS
from ..models import LeaveType, LeaveBalance, LeaveRequest
from ..forms import LeaveTypeForm, LeaveBalanceForm, LeaveRequestForm


# ==================== LeaveType ====================

class LeaveTypeListView(SortMixin, ListActionMixin, HRRequiredMixin, ListView):
    model = LeaveType
    template_name = 'leave_type/list.html'
    context_object_name = 'items'
    paginate_by = 25
    create_button_label = '新增假別'
    allowed_sort_fields = ['code', 'name', 'is_paid', 'max_hours_per_year', 'sort_order']
    default_sort = ['sort_order']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '假別設定'
        context['custom_create_url'] = reverse_lazy('hr:leave_type_create')
        return context


class LeaveTypeCreateView(CopyMixin, HRRequiredMixin, CreateView):
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


class LeaveTypeUpdateView(PrevNextMixin, HRRequiredMixin, UpdateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'leave_type/form.html'
    prev_next_order_field = 'sort_order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯假別 - {self.object.name}'
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '假別已更新。')
        return redirect('hr:leave_type_update', pk=self.object.pk)


class LeaveTypeDeleteView(SoftDeleteMixin, HRRequiredMixin, DeleteView):
    model = LeaveType
    success_url = reverse_lazy('hr:leave_type_list')


# ==================== LeaveBalance ====================

class LeaveBalanceListView(OwnEmployeeDataMixin, SortMixin, SearchMixin, ListActionMixin, HRRequiredMixin, ListView):
    model = LeaveBalance
    template_name = 'leave_balance/list.html'
    context_object_name = 'items'
    paginate_by = 25
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    create_button_label = '新增餘額'
    search_fields = ['employee__name', 'employee__employee_number']
    allowed_sort_fields = ['employee__name', 'leave_type__name', 'year', 'entitled_hours', 'used_hours']
    default_sort = ['employee__name', 'leave_type__name']

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee', 'leave_type')
        year = self.request.GET.get('year')
        if year:
            qs = qs.filter(year=year)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '假期餘額'
        context['custom_create_url'] = reverse_lazy('hr:leave_balance_create')
        context['selected_year'] = self.request.GET.get('year', '')
        context['years'] = sorted(
            LeaveBalance.objects.filter(is_deleted=False)
            .values_list('year', flat=True).distinct(),
            reverse=True,
        )
        return context


class LeaveBalanceCreateView(HRRequiredMixin, CreateView):
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


class LeaveBalanceUpdateView(OwnEmployeeDataMixin, HRRequiredMixin, UpdateView):
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'leave_balance/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯餘額 - {self.object.employee.name} / {self.object.leave_type.name}'
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '假期餘額已更新。')
        return redirect('hr:leave_balance_update', pk=self.object.pk)


class LeaveBalanceDeleteView(OwnEmployeeDataMixin, SoftDeleteMixin, HRRequiredMixin, DeleteView):
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    model = LeaveBalance
    success_url = reverse_lazy('hr:leave_balance_list')


class RecalculateLeaveView(HRRequiredMixin, View):
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

class LeaveRequestListView(OwnEmployeeDataMixin, SearchMixin, ListActionMixin, HRRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'leave_request/list.html'
    context_object_name = 'items'
    paginate_by = 25
    create_button_label = '新增請假'
    search_fields = ['employee__name', 'leave_type__name']
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee', 'leave_type')
        status = self.request.GET.get('status', 'pending')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '請假管理'
        context['custom_create_url'] = reverse_lazy('hr:leave_request_create')
        context['selected_status'] = self.request.GET.get('status', 'pending')
        return context


_HR_STAFF_GROUPS = ['CPA', 'management', 'Admin', '人資組']


def _is_hr_staff(user):
    return user.is_superuser or user.groups.filter(name__in=_HR_STAFF_GROUPS).exists()


class LeaveRequestCreateView(HRRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leave_request/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:leave_request_update', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        emp = getattr(self.request.user, 'employee_profile', None)
        if emp and not _is_hr_staff(self.request.user):
            initial['employee'] = emp
        return initial

    def get_form(self, form_class=None):
        from django import forms as dj_forms
        form = super().get_form(form_class)
        if not _is_hr_staff(self.request.user):
            form.fields['employee'].widget = dj_forms.HiddenInput()
        return form

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


class LeaveRequestUpdateView(OwnEmployeeDataMixin, PrevNextMixin, HRRequiredMixin, UpdateView):
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leave_request/form.html'
    prev_next_order_field = '-start_datetime'

    def get_form(self, form_class=None):
        from django import forms as dj_forms
        form = super().get_form(form_class)
        if not _is_hr_staff(self.request.user):
            form.fields['employee'].widget = dj_forms.HiddenInput()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯請假單 - {self.object.employee.name}'

        approval_request = self.object.get_approval_request()
        context['approval_request'] = approval_request
        if approval_request:
            context['can_approve'] = self.object.can_user_approve(self.request.user)
        else:
            context['can_approve'] = False

        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list

        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '請假單已更新。')
        return redirect('hr:leave_request_update', pk=self.object.pk)


class LeaveRequestDeleteView(OwnEmployeeDataMixin, SoftDeleteMixin, HRRequiredMixin, DeleteView):
    """Cancel (soft delete) a leave request and rollback balance"""
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    model = LeaveRequest
    success_url = reverse_lazy('hr:leave_request_list')

    def form_valid(self, _form):
        self.object = self.get_object()
        self.object.cancel()  # This handles status + balance rollback
        messages.success(self.request, '請假單已取消，餘額已回沖。')
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
