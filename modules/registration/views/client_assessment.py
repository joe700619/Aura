from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from core.mixins import ListActionMixin, PrevNextMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import ClientAssessment
from ..forms import ClientAssessmentForm, CaseAssessmentFormSet
from modules.workflow.services import (
    initiate_approval,
    submit_for_approval,
    approve,
    reject,
    return_for_revision,
    cancel_approval,
    get_effective_approver
)

class ClientAssessmentListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = ClientAssessment
    template_name = 'client_assessment/list.html'
    context_object_name = 'assessments'
    paginate_by = 20
    create_button_label = '新增評估表'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = 'registration:client_assessment'
        context['model_app_label'] = 'registration'
        return context

class ClientAssessmentCreateView(LoginRequiredMixin, CreateView):
    model = ClientAssessment
    form_class = ClientAssessmentForm
    template_name = 'client_assessment/form.html'
    success_url = reverse_lazy('registration:client_assessment_list')

class ClientAssessmentUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = ClientAssessment
    form_class = ClientAssessmentForm
    template_name = 'client_assessment/form.html'
    success_url = reverse_lazy('registration:client_assessment_list')
    prev_next_order_field = 'created_at'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['case_assessment_formset'] = CaseAssessmentFormSet(self.request.POST, instance=self.object)
        else:
            context['case_assessment_formset'] = CaseAssessmentFormSet(instance=self.object)
            
        # 添加核准相關 context
        approval_request = self.object.get_approval_request()
        context['approval_request'] = approval_request
        
        # 檢查當前使用者是否可以核准
        if approval_request:
            context['can_approve'] = self.object.can_user_approve(self.request.user)
        else:
            context['can_approve'] = False
            
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        case_assessment_formset = context['case_assessment_formset']
        if case_assessment_formset.is_valid():
            self.object = form.save()
            case_assessment_formset.instance = self.object
            case_assessment_formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class ClientAssessmentDeleteView(LoginRequiredMixin, DeleteView):
    model = ClientAssessment
    success_url = reverse_lazy('registration:client_assessment_list')
    template_name = 'client_assessment/confirm_delete.html'

# ========== Approval Action Views ==========

@login_required
def client_assessment_submit_approval(request, pk):
    """送出客戶評估核准"""
    assessment = get_object_or_404(ClientAssessment, pk=pk)
    
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
            
            messages.success(request, f'客戶評估 {assessment} 已成功送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')
    
    return redirect('registration:client_assessment_update', pk=pk)


@login_required
def client_assessment_approve(request, pk):
    """核准客戶評估"""
    assessment = get_object_or_404(ClientAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:client_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(assessment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            approve(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.success(request, f'您已核准客戶評估 {assessment} 的申請')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')
    
    return redirect('registration:client_assessment_update', pk=pk)


@login_required
def client_assessment_reject(request, pk):
    """拒絕客戶評估申請"""
    assessment = get_object_or_404(ClientAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:client_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        if not comments:
            messages.error(request, '請填寫拒絕理由')
            return redirect('registration:client_assessment_update', pk=pk)
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(assessment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            reject(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.warning(request, f'您已拒絕客戶評估 {assessment} 的申請')
        except Exception as e:
            messages.error(request, f'拒絕失敗：{str(e)}')
    
    return redirect('registration:client_assessment_update', pk=pk)


@login_required
def client_assessment_return(request, pk):
    """退回客戶評估申請"""
    assessment = get_object_or_404(ClientAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:client_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        if not comments:
            messages.error(request, '請填寫退回理由')
            return redirect('registration:client_assessment_update', pk=pk)
        
        try:
            # 檢查是否為代理人
            step_approver = approval_request.current_step.get_approver(assessment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            
            as_delegate_for = original if effective_approver == request.user and original else None
            
            return_for_revision(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            
            messages.info(request, f'已退回客戶評估 {assessment} 的申請，請申請人修正後重新送出')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')
    
    return redirect('registration:client_assessment_update', pk=pk)


@login_required
def client_assessment_cancel_approval(request, pk):
    """撤回客戶評估申請"""
    assessment = get_object_or_404(ClientAssessment, pk=pk)
    approval_request = assessment.get_approval_request()
    
    if not approval_request or not assessment.can_user_cancel(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('registration:client_assessment_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        
        try:
            cancel_approval(approval_request, request.user, comments)
            
            messages.info(request, f'您已撤回客戶評估 {assessment} 的申請')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')
    
    return redirect('registration:client_assessment_update', pk=pk)
