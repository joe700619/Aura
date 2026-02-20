from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from core.mixins import ListActionMixin, PrevNextMixin
from ..models import CaseAssessment
from ..forms import CaseAssessmentCRUDForm
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

class CaseAssessmentListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = CaseAssessment
    template_name = 'case_assessment/list.html'
    context_object_name = 'assessments'
    paginate_by = 20
    create_button_label = '新增案件評估表'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = 'caseassessment'
        context['model_app_label'] = 'registration'
        return context

class CaseAssessmentCreateView(LoginRequiredMixin, CreateView):
    model = CaseAssessment
    form_class = CaseAssessmentCRUDForm
    template_name = 'case_assessment/form.html'
    success_url = reverse_lazy('registration:case_assessment_list')

    def form_valid(self, form):
        from ..models import ClientAssessment
        client_id = form.cleaned_data.get('search_customer')
        if client_id:
            try:
                client = ClientAssessment.objects.get(pk=client_id)
                form.instance.client_assessment = client
            except ClientAssessment.DoesNotExist:
                pass
        return super().form_valid(form)

class CaseAssessmentUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = CaseAssessment
    form_class = CaseAssessmentCRUDForm
    template_name = 'case_assessment/form.html'
    success_url = reverse_lazy('registration:case_assessment_list')
    prev_next_order_field = 'created_at'

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

class CaseAssessmentDeleteView(LoginRequiredMixin, DeleteView):
    model = CaseAssessment
    success_url = reverse_lazy('registration:case_assessment_list')
    template_name = 'case_assessment/confirm_delete.html'

# ========== Approval Action Views ==========

@login_required
def case_assessment_submit_approval(request, pk):
    """送出案件評估核准"""
    assessment = get_object_or_404(CaseAssessment, pk=pk)
    
    if request.method == 'POST':
        try:
            # 取得或建立核准請求
            approval_request = assessment.get_approval_request()
            
            if not approval_request:
                # 建立新的核准請求，使用 'anti_money_laundering' 工作流程代碼
                approval_request = initiate_approval(
                    obj=assessment,
                    workflow_code='anti_money_laundering',
                    requester=request.user
                )
            
            # 送出核准
            submit_for_approval(approval_request, comments='')
            
            messages.success(request, f'案件評估 {assessment} 已成功送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')
    
    return redirect('registration:case_assessment_update', pk=pk)


@login_required
def case_assessment_approve(request, pk):
    """核准案件評估"""
    assessment = get_object_or_404(CaseAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:case_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(assessment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            approve(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.success(request, f'您已核准案件評估 {assessment} 的申請')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')
    
    return redirect('registration:case_assessment_update', pk=pk)


@login_required
def case_assessment_reject(request, pk):
    """拒絕案件評估申請"""
    assessment = get_object_or_404(CaseAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:case_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        if not comments:
            messages.error(request, '請填寫拒絕理由')
            return redirect('registration:case_assessment_update', pk=pk)
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(assessment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            reject(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.warning(request, f'您已拒絕案件評估 {assessment} 的申請')
        except Exception as e:
            messages.error(request, f'拒絕失敗：{str(e)}')
    
    return redirect('registration:case_assessment_update', pk=pk)


@login_required
def case_assessment_return(request, pk):
    """退回案件評估申請"""
    assessment = get_object_or_404(CaseAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:case_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        if not comments:
            messages.error(request, '請填寫退回理由')
            return redirect('registration:case_assessment_update', pk=pk)
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(assessment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            return_for_revision(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.info(request, f'已退回案件評估 {assessment} 的申請，請申請人修正後重新送出')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')
    
    return redirect('registration:case_assessment_update', pk=pk)


@login_required
def case_assessment_cancel_approval(request, pk):
    """撤回案件評估申請"""
    assessment = get_object_or_404(CaseAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_cancel(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:case_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        try:
            cancel_approval(approval_request, request.user, comments)
            
            messages.info(request, f'您已撤回案件評估 {assessment} 的申請')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')
    
    return redirect('registration:case_assessment_update', pk=pk)
