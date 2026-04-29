from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

from core.mixins import HRRequiredMixin, ListActionMixin, CopyMixin, PrevNextMixin, SortMixin
from ..models import Employee
from ..forms import EmployeeForm


class EmployeeListView(SortMixin, ListActionMixin, HRRequiredMixin, ListView):
    """員工列表視圖"""
    model = Employee
    template_name = 'employee/list.html'
    context_object_name = 'employees'
    paginate_by = 25
    create_button_label = '新增員工'
    allowed_sort_fields = ['employee_number', 'name', 'gender', 'team', 'employment_status', 'hire_date']
    default_sort = ['-employee_number']

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class EmployeeCreateView(CopyMixin, HRRequiredMixin, CreateView):
    """員工新增視圖"""
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/form.html'
    success_url = reverse_lazy('hr:employee_list')
    copy_exclude_fields = []  # 複製時不排除任何欄位


class EmployeeUpdateView(PrevNextMixin, HRRequiredMixin, UpdateView):
    """員工編輯視圖"""
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/form.html'
    success_url = reverse_lazy('hr:employee_list')

    # PrevNextMixin 設定
    prev_next_order_field = 'employee_number'  # 按員工編號排序

    def get_nav_queryset(self):
        return self.model.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 添加核准相關 context
        approval_request = self.object.get_approval_request()
        context['approval_request'] = approval_request
        
        # 檢查當前使用者是否可以核准
        if approval_request:
            context['can_approve'] = self.object.can_user_approve(self.request.user)
        else:
            context['can_approve'] = False
        
        return context


class EmployeeDeleteView(HRRequiredMixin, UpdateView):
    """員工刪除視圖（軟刪除）"""
    model = Employee
    fields = []
    template_name = 'employee/confirm_delete.html'
    success_url = reverse_lazy('hr:employee_list')
    
    def form_valid(self, form):
        """軟刪除：設置 is_active 為 False"""
        self.object.is_active = False
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


# ========== Approval Action Views ==========

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from modules.workflow.services import (
    initiate_approval,
    submit_for_approval,
    approve,
    reject,
    return_for_revision,
    cancel_approval,
    get_effective_approver
)


@login_required
def employee_submit_approval(request, pk):
    """送出員工核准"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        try:
            # 取得或建立核准請求
            approval_request = employee.get_approval_request()
            
            if not approval_request:
                # 建立新的核准請求
                approval_request = initiate_approval(
                    obj=employee,
                    workflow_code='employee_onboarding',
                    requester=request.user
                )
            
            # 送出核准
            submit_for_approval(approval_request, comments='')
            
            messages.success(request, f'員工 {employee.name} 已成功送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')
    
    return redirect('hr:employee_update', pk=pk)


@login_required
def employee_approve(request, pk):
    """核准員工"""
    employee = get_object_or_404(Employee, pk=pk)
    approval_request = employee.get_approval_request()
    
    if not approval_request or not employee.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('hr:employee_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(employee)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            approve(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.success(request, f'您已核准員工 {employee.name} 的申請')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')
    
    return redirect('hr:employee_update', pk=pk)


@login_required
def employee_reject(request, pk):
    """拒絕員工申請"""
    employee = get_object_or_404(Employee, pk=pk)
    approval_request = employee.get_approval_request()
    
    if not approval_request or not employee.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('hr:employee_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        if not comments:
            messages.error(request, '請填寫拒絕理由')
            return redirect('hr:employee_update', pk=pk)
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(employee)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            reject(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.warning(request, f'您已拒絕員工 {employee.name} 的申請')
        except Exception as e:
            messages.error(request, f'拒絕失敗：{str(e)}')
    
    return redirect('hr:employee_update', pk=pk)


@login_required
def employee_return(request, pk):
    """退回員工申請"""
    employee = get_object_or_404(Employee, pk=pk)
    approval_request = employee.get_approval_request()
    
    if not approval_request or not employee.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('hr:employee_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        if not comments:
            messages.error(request, '請填寫退回理由')
            return redirect('hr:employee_update', pk=pk)
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(employee)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            return_for_revision(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.info(request, f'已退回員工 {employee.name} 的申請，請申請人修正後重新送出')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')
    
    return redirect('hr:employee_update', pk=pk)


@login_required
def employee_cancel_approval(request, pk):
    """撤回員工申請"""
    employee = get_object_or_404(Employee, pk=pk)
    approval_request = employee.get_approval_request()
    
    if not approval_request or not employee.can_user_cancel(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('hr:employee_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        try:
            cancel_approval(approval_request, request.user, comments)
            
            messages.info(request, f'您已撤回員工 {employee.name} 的申請')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')
    
    return redirect('hr:employee_update', pk=pk)
