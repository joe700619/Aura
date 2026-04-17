from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, PrevNextMixin, FilterMixin
from ..models import IrsAuditNotice, IrsAuditNoticeAttachment
from ..forms import IrsAuditNoticeForm, IrsAuditCommunicationFormSet
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from modules.basic_data.models import Customer
from modules.workflow.services import (
    initiate_approval,
    submit_for_approval,
    approve,
    reject,
    return_for_revision,
    cancel_approval,
    get_effective_approver
)

class IrsAuditNoticeListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = IrsAuditNotice
    template_name = 'administrative/irs_audit_notice/list.html'
    context_object_name = 'notices'
    paginate_by = 25
    create_button_label = '新增國稅局查帳通知'
    search_fields = ['customer__name', 'subject', 'tax_id', 'tax_category']
    filter_choices = {
        'pending':    {'status': '待處理'},
        'processing': {'status': '處理中'},
        'closed':     {'status': '已結案'},
    }
    default_filter = 'pending'

    def get_base_queryset(self):
        return super().get_base_queryset().select_related('customer')

    def _base_qs_for_counts(self):
        return self.model.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = 'irsauditnotice'
        context['model_app_label'] = 'administrative'
        return context

class IrsAuditNoticeCreateView(BusinessRequiredMixin, CreateView):
    model = IrsAuditNotice
    form_class = IrsAuditNoticeForm
    template_name = 'administrative/irs_audit_notice/form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['communications'] = IrsAuditCommunicationFormSet(self.request.POST)
        else:
            data['communications'] = IrsAuditCommunicationFormSet()
        data['attachments'] = []
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        communications = context['communications']
        if communications.is_valid():
            with transaction.atomic():
                self.object = form.save()
                communications.instance = self.object
                communications.save()
                for f in self.request.FILES.getlist('new_attachments'):
                    IrsAuditNoticeAttachment.objects.create(notice=self.object, file=f)
            messages.success(self.request, '新增國稅局查帳通知成功。')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('administrative:irs_audit_notice_update', kwargs={'pk': self.object.pk})

class IrsAuditNoticeUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = IrsAuditNotice
    form_class = IrsAuditNoticeForm
    template_name = 'administrative/irs_audit_notice/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        return reverse_lazy('administrative:irs_audit_notice_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['communications'] = IrsAuditCommunicationFormSet(self.request.POST, instance=self.object)
        else:
            data['communications'] = IrsAuditCommunicationFormSet(instance=self.object)

        if self.object:
            data['attachments'] = self.object.attachments.all()

        # Approval related context
        approval_request = self.object.get_approval_request()
        data['approval_request'] = approval_request

        if approval_request:
            data['can_approve'] = self.object.can_user_approve(self.request.user)
        else:
            data['can_approve'] = False

        # History
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            data['history'] = history_list

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        communications = context['communications']
        if communications.is_valid():
            with transaction.atomic():
                self.object = form.save()
                communications.instance = self.object
                communications.save()

                deleted_ids_str = self.request.POST.get('deleted_attachment_ids', '')
                if deleted_ids_str:
                    id_list = [i.strip() for i in deleted_ids_str.split(',') if i.strip().isdigit()]
                    if id_list:
                        IrsAuditNoticeAttachment.objects.filter(id__in=id_list, notice=self.object).delete()

                for f in self.request.FILES.getlist('new_attachments'):
                    IrsAuditNoticeAttachment.objects.create(notice=self.object, file=f)

            messages.success(self.request, '更新國稅局查帳通知成功。')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

class IrsAuditNoticeDeleteView(BusinessRequiredMixin, DeleteView):
    model = IrsAuditNotice
    success_url = reverse_lazy('administrative:irs_audit_notice_list')
    template_name = 'administrative/irs_audit_notice/confirm_delete.html'


def get_customer_tax_id(request):
    """Ajax endpoint to fetch Customer Tax ID given their ID"""
    customer_id = request.GET.get('customer_id')
    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
            return JsonResponse({'tax_id': customer.tax_id})
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=404)
    return JsonResponse({'error': 'No customer_id provided'}, status=400)


# ========== Approval Action Views ==========

@login_required
def irs_audit_notice_submit_approval(request, pk):
    """送出核准"""
    notice = get_object_or_404(IrsAuditNotice, pk=pk)
    if request.method == 'POST':
        try:
            approval_request = notice.get_approval_request()
            if not approval_request:
                # Assuming 'anti_money_laundering' or similar workflow, lets just use a generic or 'sign_off'
                # or we can reuse `anti_money_laundering` if needed. Let's assume a generic one exists.
                # Here we reuse the code from `case_assessment` but there might not be a specific code.
                approval_request = initiate_approval(
                    obj=notice,
                    workflow_code='irs_audit',
                    requester=request.user
                )
            submit_for_approval(approval_request, comments='')
            messages.success(request, f'查帳通知 {notice} 已成功送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')
    return redirect('administrative:irs_audit_notice_update', pk=pk)

@login_required
def irs_audit_notice_approve(request, pk):
    """核准"""
    notice = get_object_or_404(IrsAuditNotice, pk=pk)
    approval_request = notice.get_approval_request()
    
    if not approval_request or not notice.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:irs_audit_notice_update', pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        try:
            step_approver = approval_request.current_step.get_approver(notice)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            as_delegate_for = original if effective_approver == request.user and original else None
            
            approve(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            messages.success(request, f'您已核准申請')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')
            
    return redirect('administrative:irs_audit_notice_update', pk=pk)

@login_required
def irs_audit_notice_reject(request, pk):
    """拒絕"""
    notice = get_object_or_404(IrsAuditNotice, pk=pk)
    approval_request = notice.get_approval_request()
    
    if not approval_request or not notice.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:irs_audit_notice_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        if not comments:
            messages.error(request, '請填寫拒絕理由')
            return redirect('administrative:irs_audit_notice_update', pk=pk)
        try:
            step_approver = approval_request.current_step.get_approver(notice)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            as_delegate_for = original if effective_approver == request.user and original else None
            
            reject(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            messages.warning(request, f'您已拒絕申請')
        except Exception as e:
            messages.error(request, f'拒絕失敗：{str(e)}')
            
    return redirect('administrative:irs_audit_notice_update', pk=pk)

@login_required
def irs_audit_notice_return(request, pk):
    """退回"""
    notice = get_object_or_404(IrsAuditNotice, pk=pk)
    approval_request = notice.get_approval_request()
    
    if not approval_request or not notice.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:irs_audit_notice_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        if not comments:
            messages.error(request, '請填寫退回理由')
            return redirect('administrative:irs_audit_notice_update', pk=pk)
        try:
            step_approver = approval_request.current_step.get_approver(notice)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            as_delegate_for = original if effective_approver == request.user and original else None
            
            return_for_revision(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            messages.info(request, f'已退回申請，請申請人修正後重新送出')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')
            
    return redirect('administrative:irs_audit_notice_update', pk=pk)

@login_required
def irs_audit_notice_cancel_approval(request, pk):
    """撤回申請"""
    notice = get_object_or_404(IrsAuditNotice, pk=pk)
    approval_request = notice.get_approval_request()
    
    if not approval_request or not notice.can_user_cancel(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:irs_audit_notice_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        try:
            cancel_approval(approval_request, request.user, comments)
            messages.info(request, f'您已撤回申請')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')
            
    return redirect('administrative:irs_audit_notice_update', pk=pk)
