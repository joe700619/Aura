from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.mixins import CopyMixin, PrevNextMixin, ListActionMixin
from ..models import SalaryStructure, OvertimeRecord, PayrollRecord, Employee, InsuranceBracket, AdvancePayment
from ..forms import SalaryStructureForm, OvertimeRecordForm, PayrollRecordForm, InsuranceBracketForm, AdvancePaymentForm
from modules.workflow.services import (
    initiate_approval,
    submit_for_approval,
    approve as workflow_approve,
    reject as workflow_reject,
    return_for_revision,
    cancel_approval,
    get_effective_approver,
)


# ==================== InsuranceBracket ====================

class InsuranceBracketListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = InsuranceBracket
    template_name = 'insurance_bracket/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增級距'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(level_name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '勞健保投保級距表'
        context['custom_create_url'] = reverse_lazy('hr:insurance_bracket_create')
        context['q'] = self.request.GET.get('q', '')
        return context


class InsuranceBracketCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = InsuranceBracket
    form_class = InsuranceBracketForm
    template_name = 'insurance_bracket/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:insurance_bracket_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增級距'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '投保級距已建立。')
        return redirect(self.get_success_url())


class InsuranceBracketUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = InsuranceBracket
    form_class = InsuranceBracketForm
    template_name = 'insurance_bracket/form.html'
    prev_next_order_field = 'insured_salary'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯級距 - {self.object.level_name}'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '投保級距已更新。')
        return redirect('hr:insurance_bracket_update', pk=self.object.pk)


class InsuranceBracketDeleteView(LoginRequiredMixin, DeleteView):
    model = InsuranceBracket
    success_url = reverse_lazy('hr:insurance_bracket_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# ==================== SalaryStructure ====================

class SalaryStructureListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = SalaryStructure
    template_name = 'salary_structure/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增薪資結構'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee')
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(employee__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '薪資結構'
        context['custom_create_url'] = reverse_lazy('hr:salary_structure_create')
        context['q'] = self.request.GET.get('q', '')
        return context


class SalaryStructureCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'salary_structure/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:salary_structure_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增薪資結構'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '薪資結構已建立。')
        return redirect(self.get_success_url())


class SalaryStructureUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'salary_structure/form.html'
    prev_next_order_field = '-effective_date'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯薪資結構 - {self.object.employee.name}'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '薪資結構已更新。')
        return redirect('hr:salary_structure_update', pk=self.object.pk)


class SalaryStructureDeleteView(LoginRequiredMixin, DeleteView):
    model = SalaryStructure
    success_url = reverse_lazy('hr:salary_structure_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# ==================== OvertimeRecord ====================

class OvertimeListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = OvertimeRecord
    template_name = 'overtime/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增加班'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee')
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(employee__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '加班紀錄'
        context['custom_create_url'] = reverse_lazy('hr:overtime_create')
        context['q'] = self.request.GET.get('q', '')
        return context


class OvertimeCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = OvertimeRecord
    form_class = OvertimeRecordForm
    template_name = 'overtime/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:overtime_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增加班紀錄'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '加班紀錄已建立。')
        return redirect(self.get_success_url())


class OvertimeUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = OvertimeRecord
    form_class = OvertimeRecordForm
    template_name = 'overtime/form.html'
    prev_next_order_field = '-date'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯加班紀錄 - {self.object.employee.name}'

        # 添加核准相關 context
        approval_request = self.object.get_approval_request()
        context['approval_request'] = approval_request
        context['can_approve'] = self.object.can_user_approve(self.request.user) if approval_request else False

        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '加班紀錄已更新。')
        return redirect('hr:overtime_update', pk=self.object.pk)


class OvertimeDeleteView(LoginRequiredMixin, DeleteView):
    model = OvertimeRecord
    success_url = reverse_lazy('hr:overtime_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# ==================== PayrollRecord ====================

class PayrollListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = PayrollRecord
    template_name = 'payroll/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增薪資單'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee')
        q = self.request.GET.get('q', '')
        year_month = self.request.GET.get('year_month', '')
        status = self.request.GET.get('status', 'draft')
        
        if q:
            qs = qs.filter(employee__name__icontains=q)
        if year_month:
            qs = qs.filter(year_month=year_month)
            
        if status == 'draft':
            qs = qs.filter(is_finalized=False)
        elif status == 'finalized':
            qs = qs.filter(is_finalized=True)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '薪資單'
        context['custom_create_url'] = reverse_lazy('hr:payroll_create')
        context['q'] = self.request.GET.get('q', '')
        context['selected_year_month'] = self.request.GET.get('year_month', '')
        context['selected_status'] = self.request.GET.get('status', 'draft')
        return context


class PayrollCreateView(LoginRequiredMixin, CreateView):
    model = PayrollRecord
    form_class = PayrollRecordForm
    template_name = 'payroll/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:payroll_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增薪資單'
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.calculate()
        self.object.save()
        messages.success(self.request, '薪資單已建立並自動計算。')
        return redirect(self.get_success_url())


class PayrollUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = PayrollRecord
    form_class = PayrollRecordForm
    template_name = 'payroll/form.html'
    prev_next_order_field = '-year_month'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'薪資單 - {self.object.employee.name} ({self.object.year_month})'
        return context

    def form_valid(self, form):
        self.object = form.save()
        
        # 當薪資單從草稿轉為已確認時，將關聯的代墊款標記為已發放
        if self.object.is_finalized:
            approved_advances = AdvancePayment.objects.filter(
                employee=self.object.employee,
                status='approved',
                is_deleted=False,
            )
            updated_count = 0
            for ap in approved_advances:
                ap.status = 'deducted'
                ap.payroll_record = self.object
                ap.save()
                updated_count += 1
            if updated_count:
                messages.info(self.request, f'已將 {updated_count} 筆代墊款標記為已發放 (依附此薪資單)。')
        
        messages.success(self.request, '薪資單已更新。')
        return redirect('hr:payroll_update', pk=self.object.pk)


class PayrollDeleteView(LoginRequiredMixin, DeleteView):
    model = PayrollRecord
    success_url = reverse_lazy('hr:payroll_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


class PayrollBatchGenerateView(LoginRequiredMixin, View):
    """批次產生薪資單"""

    def post(self, request):
        year_month = request.POST.get('year_month', '')
        if not year_month or len(year_month) != 7:
            messages.error(request, '請輸入正確的年月格式 (例如: 2026-03)。')
            return redirect('hr:payroll_list')

        employees = Employee.objects.filter(employment_status='ACTIVE', is_active=True)
        created_count = 0
        for emp in employees:
            # Skip if already exists
            if PayrollRecord.objects.filter(employee=emp, year_month=year_month).exists():
                continue
            record = PayrollRecord(employee=emp, year_month=year_month)
            record.calculate()
            record.save()
            created_count += 1

        messages.success(request, f'已為 {created_count} 位員工產生 {year_month} 薪資單。')
        return redirect(f"{reverse_lazy('hr:payroll_list')}?year_month={year_month}")


# ==================== AdvancePayment ====================

class AdvancePaymentListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = AdvancePayment
    template_name = 'advance_payment/list.html'
    context_object_name = 'items'
    paginate_by = 30
    create_button_label = '新增代墊款'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee', 'payroll_record')
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(employee__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '代墊款申請'
        context['custom_create_url'] = reverse_lazy('hr:advance_payment_create')
        context['q'] = self.request.GET.get('q', '')
        return context


class AdvancePaymentCreateView(LoginRequiredMixin, CreateView):
    model = AdvancePayment
    form_class = AdvancePaymentForm
    template_name = 'advance_payment/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:advance_payment_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增代墊款申請'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '代墊款申請已建立。')
        return redirect(self.get_success_url())


class AdvancePaymentUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = AdvancePayment
    form_class = AdvancePaymentForm
    template_name = 'advance_payment/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:advance_payment_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context['page_title'] = f'編輯代墊款申請: {obj.employee.name}'

        # Workflow approval context
        approval_request = obj.get_approval_request()
        context['approval_request'] = approval_request
        if approval_request:
            context['can_approve'] = obj.can_user_approve(self.request.user)
        else:
            context['can_approve'] = False

        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '代墊款申請已更新。')
        return redirect(self.get_success_url())


class AdvancePaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = AdvancePayment
    success_url = reverse_lazy('hr:advance_payment_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# ========== Advance Payment Approval Action Views ==========

@login_required
def advancepayment_submit_approval(request, pk):
    """送出代墊款核准"""
    obj = get_object_or_404(AdvancePayment, pk=pk)

    if request.method == 'POST':
        try:
            approval_request = obj.get_approval_request()
            if not approval_request:
                approval_request = initiate_approval(
                    obj=obj,
                    workflow_code='advanced_payment_request',
                    requester=request.user,
                )
            submit_for_approval(approval_request, comments='')
            messages.success(request, f'{obj.employee.name} 的代墊款已送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')

    return redirect('hr:advance_payment_update', pk=pk)


@login_required
def advancepayment_approve(request, pk):
    """核准代墊款"""
    obj = get_object_or_404(AdvancePayment, pk=pk)

    if request.method == 'POST':
        approval_request = obj.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:advance_payment_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            workflow_approve(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            # 核准通過後更新代墊款狀態
            if approval_request.status == 'APPROVED':
                obj.status = 'approved'
                obj.is_approved = True
                obj.approved_by = request.user
                obj.save(update_fields=['status', 'is_approved', 'approved_by'])
            messages.success(request, '代墊款已核准。')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')

    return redirect('hr:advance_payment_update', pk=pk)


@login_required
def advancepayment_reject(request, pk):
    """駁回代墊款"""
    obj = get_object_or_404(AdvancePayment, pk=pk)

    if request.method == 'POST':
        approval_request = obj.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:advance_payment_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            workflow_reject(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            obj.status = 'rejected'
            obj.save(update_fields=['status'])
            messages.success(request, '代墊款已駁回。')
        except Exception as e:
            messages.error(request, f'駁回失敗：{str(e)}')

    return redirect('hr:advance_payment_update', pk=pk)


@login_required
def advancepayment_return(request, pk):
    """退回代墊款"""
    obj = get_object_or_404(AdvancePayment, pk=pk)

    if request.method == 'POST':
        approval_request = obj.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:advance_payment_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            return_for_revision(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            messages.success(request, '代墊款已退回申請人修正。')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')

    return redirect('hr:advance_payment_update', pk=pk)


@login_required
def advancepayment_cancel_approval(request, pk):
    """撤回代墊款核准"""
    obj = get_object_or_404(AdvancePayment, pk=pk)

    if request.method == 'POST':
        approval_request = obj.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:advance_payment_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            cancel_approval(approval_request, requester=request.user, comments=comments)
            messages.success(request, '代墊款核准已撤回。')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')

    return redirect('hr:advance_payment_update', pk=pk)



# ========== Overtime Approval Action Views ==========



@login_required
def overtime_submit_approval(request, pk):
    """送出加班單核准"""
    ot = get_object_or_404(OvertimeRecord, pk=pk)

    if request.method == 'POST':
        try:
            approval_request = ot.get_approval_request()
            if not approval_request:
                approval_request = initiate_approval(
                    obj=ot,
                    workflow_code='overtime_record',
                    requester=request.user,
                )
            submit_for_approval(approval_request, comments='')
            messages.success(request, f'{ot.employee.name} 的加班單已送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')

    return redirect('hr:overtime_update', pk=pk)


@login_required
def overtime_approve(request, pk):
    """核准加班單"""
    ot = get_object_or_404(OvertimeRecord, pk=pk)

    if request.method == 'POST':
        approval_request = ot.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:overtime_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            workflow_approve(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            if approval_request.status == 'APPROVED':
                ot.is_approved = True
                ot.approved_by = request.user
                ot.save(update_fields=['is_approved', 'approved_by'])
            messages.success(request, '加班單已核准。')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')

    return redirect('hr:overtime_update', pk=pk)


@login_required
def overtime_reject(request, pk):
    """拒絕加班單"""
    ot = get_object_or_404(OvertimeRecord, pk=pk)

    if request.method == 'POST':
        approval_request = ot.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:overtime_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            workflow_reject(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            messages.success(request, '加班單已駁回。')
        except Exception as e:
            messages.error(request, f'駁回失敗：{str(e)}')

    return redirect('hr:overtime_update', pk=pk)


@login_required
def overtime_return(request, pk):
    """退回加班單"""
    ot = get_object_or_404(OvertimeRecord, pk=pk)

    if request.method == 'POST':
        approval_request = ot.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:overtime_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            effective_approver, original = get_effective_approver(request.user, approval_request)
            return_for_revision(
                approval_request,
                approver=request.user,
                comments=comments,
                as_delegate_for=original,
            )
            messages.success(request, '加班單已退回申請人修正。')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')

    return redirect('hr:overtime_update', pk=pk)


@login_required
def overtime_cancel_approval(request, pk):
    """撤回加班單核准"""
    ot = get_object_or_404(OvertimeRecord, pk=pk)

    if request.method == 'POST':
        approval_request = ot.get_approval_request()
        if not approval_request:
            messages.error(request, '找不到核准請求。')
            return redirect('hr:overtime_update', pk=pk)

        comments = request.POST.get('comments', '')
        try:
            cancel_approval(approval_request, requester=request.user, comments=comments)
            messages.success(request, '加班單核准已撤回。')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')

    return redirect('hr:overtime_update', pk=pk)
