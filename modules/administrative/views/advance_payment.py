from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.utils import timezone

from core.mixins import ListActionMixin, PrevNextMixin, SoftDeleteMixin
from modules.workflow.services import (
    initiate_approval,
    submit_for_approval,
    approve,
    reject,
    return_for_revision,
    cancel_approval,
    get_effective_approver
)

from ..models.advance_payment import AdvancePayment, AdvancePaymentImage
from ..forms import AdvancePaymentForm, AdvancePaymentDetailFormSet

class AdvancePaymentListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = AdvancePayment
    template_name = 'administrative/advance_payment/list.html'
    context_object_name = 'advance_payments'
    paginate_by = 20
    create_button_label = '新增代墊款'

    def get_queryset(self):
        return AdvancePayment.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '代墊款列表'
        context['custom_create_url'] = reverse_lazy('administrative:advance_payment_create')
        return context

class AdvancePaymentCreateView(LoginRequiredMixin, CreateView):
    model = AdvancePayment
    form_class = AdvancePaymentForm
    template_name = 'administrative/advance_payment/form.html'
    success_url = reverse_lazy('administrative:advance_payment_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['details'] = AdvancePaymentDetailFormSet(self.request.POST)
        else:
            context['details'] = AdvancePaymentDetailFormSet()
        context['images'] = []
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        details = context['details']

        # Auto-generate advance_no if empty
        if not form.cleaned_data.get('advance_no'):
            today = timezone.now().strftime('%Y%m%d')
            count = AdvancePayment.objects.filter(date=timezone.now().date()).count() + 1
            form.instance.advance_no = f'AP-{today}-{count:03d}'

        if details.is_valid():
            with transaction.atomic():
                form.instance.applicant = self.request.user
                self.object = form.save()
                details.instance = self.object
                details.save()
                
                # Hand images
                images = self.request.FILES.getlist('images')
                for image in images:
                    AdvancePaymentImage.objects.create(advance_payment=self.object, image=image)
                    
            messages.success(self.request, '代墊款已成功新增。')
            return redirect('administrative:advance_payment_update', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class AdvancePaymentUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = AdvancePayment
    form_class = AdvancePaymentForm
    template_name = 'administrative/advance_payment/form.html'
    success_url = reverse_lazy('administrative:advance_payment_list')
    prev_next_order_field = 'date'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['details'] = AdvancePaymentDetailFormSet(self.request.POST, instance=self.object)
        else:
            context['details'] = AdvancePaymentDetailFormSet(instance=self.object)
        
        context['images'] = self.object.images.all()

        if self.request.method == 'GET' and hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list

        # Approval related context
        approval_request = self.object.get_approval_request()
        context['approval_request'] = approval_request
        if approval_request:
            context['can_approve'] = self.object.can_user_approve(self.request.user)
        else:
            context['can_approve'] = False
            
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        details = context['details']
        
        was_posted = form.initial.get('is_posted', False)
        is_posted_now = form.cleaned_data.get('is_posted', False)
        is_newly_posted = (not was_posted) and is_posted_now

        if details.is_valid():
            with transaction.atomic():
                self.object = form.save()
                details.instance = self.object
                details.save()
                
                # Handle image deletions
                deleted_ids_str = self.request.POST.get('deleted_image_ids', '')
                if deleted_ids_str:
                    id_list = [id.strip() for id in deleted_ids_str.split(',') if id.strip().isdigit()]
                    if id_list:
                        deleted_count, _ = AdvancePaymentImage.objects.filter(id__in=id_list, advance_payment=self.object).delete()
                        if deleted_count > 0:
                            messages.info(self.request, f"已移除 {deleted_count} 張圖片。")

                # Handle new image uploads
                images = self.request.FILES.getlist('images')
                if images:
                    for image in images:
                        AdvancePaymentImage.objects.create(advance_payment=self.object, image=image)
                    messages.info(self.request, f"已上傳 {len(images)} 張新圖片。")
            
            # Auto Posting Logic
            if is_newly_posted:
                try:
                    from ..services.advance_payment_service import generate_voucher_for_advance_payment
                    with transaction.atomic():
                        voucher = generate_voucher_for_advance_payment(self.object, self.request.user)
                        if voucher:
                            messages.success(self.request, f"狀態已更新，並成功產生傳票：{voucher.voucher_no}")
                        else:
                            messages.warning(self.request, "已過帳，但無金額可產生傳票分錄。")
                except ValueError as e:
                    self.object.is_posted = False
                    self.object.save(update_fields=['is_posted'])
                    messages.error(self.request, f"產生傳票失敗：{str(e)}。已取消過帳狀態。")
                except Exception as e:
                    self.object.is_posted = False
                    self.object.save(update_fields=['is_posted'])
                    messages.error(self.request, f"產生傳票時發生系統錯誤：{str(e)}")
            else:
                if is_posted_now:
                    messages.success(self.request, "資料已更新，狀態維持過帳 (未拋轉新傳票)")
                else:
                    messages.success(self.request, "資料已成功更新 (未過帳)")

            return redirect('administrative:advance_payment_update', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class AdvancePaymentDeleteView(SoftDeleteMixin, LoginRequiredMixin, DeleteView):
    model = AdvancePayment
    template_name = 'administrative/advance_payment/confirm_delete.html'
    success_url = reverse_lazy('administrative:advance_payment_list')

# ========== Approval Action Views ==========

@login_required
def advance_payment_submit_approval(request, pk):
    payment = get_object_or_404(AdvancePayment, pk=pk)
    
    if request.method == 'POST':
        try:
            approval_request = payment.get_approval_request()
            if not approval_request:
                # Use a specific workflow code if exists, default to anti_money_laundering or standard
                # For example, using 'test' or adjusting to whatever admin configured. 
                # Let's use 'advance_payment' workflow if created, or adapt from existing.
                approval_request = initiate_approval(
                    obj=payment,
                    workflow_code='advance_payment_approval',
                    requester=request.user
                )
            submit_for_approval(approval_request, comments='')
            messages.success(request, f'代墊款 {payment} 已成功送出核准！')
        except Exception as e:
            messages.error(request, f'送出核准失敗：{str(e)}')
            
    return redirect('administrative:advance_payment_update', pk=pk)


@login_required
def advance_payment_approve(request, pk):
    payment = get_object_or_404(AdvancePayment, pk=pk)
    approval_request = payment.get_approval_request()
    
    if not approval_request or not payment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:advance_payment_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        try:
            step_approver = approval_request.current_step.get_approver(payment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            as_delegate_for = original if effective_approver == request.user and original else None
            
            approve(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            messages.success(request, f'您已核准代墊款 {payment} 的申請')
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')
            
    return redirect('administrative:advance_payment_update', pk=pk)


@login_required
def advance_payment_reject(request, pk):
    payment = get_object_or_404(AdvancePayment, pk=pk)
    approval_request = payment.get_approval_request()
    
    if not approval_request or not payment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:advance_payment_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        if not comments:
            messages.error(request, '請填寫拒絕理由')
            return redirect('administrative:advance_payment_update', pk=pk)
            
        try:
            step_approver = approval_request.current_step.get_approver(payment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            as_delegate_for = original if effective_approver == request.user and original else None
            
            reject(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            messages.warning(request, f'您已拒絕代墊款 {payment} 的申請')
        except Exception as e:
            messages.error(request, f'拒絕失敗：{str(e)}')
            
    return redirect('administrative:advance_payment_update', pk=pk)


@login_required
def advance_payment_return(request, pk):
    payment = get_object_or_404(AdvancePayment, pk=pk)
    approval_request = payment.get_approval_request()
    
    if not approval_request or not payment.can_user_approve(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:advance_payment_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        if not comments:
            messages.error(request, '請填寫退回理由')
            return redirect('administrative:advance_payment_update', pk=pk)
            
        try:
            step_approver = approval_request.current_step.get_approver(payment)
            effective_approver, original = get_effective_approver(step_approver, approval_request)
            as_delegate_for = original if effective_approver == request.user and original else None
            
            return_for_revision(approval_request, request.user, comments, as_delegate_for=as_delegate_for)
            messages.info(request, f'已退回代墊款 {payment} 的申請，請申請人修正後重新送出')
        except Exception as e:
            messages.error(request, f'退回失敗：{str(e)}')
            
    return redirect('administrative:advance_payment_update', pk=pk)


@login_required
def advance_payment_cancel_approval(request, pk):
    payment = get_object_or_404(AdvancePayment, pk=pk)
    approval_request = payment.get_approval_request()
    
    if not approval_request or not payment.can_user_cancel(request.user):
        messages.error(request, '您沒有權限執行此操作')
        return redirect('administrative:advance_payment_update', pk=pk)
        
    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        try:
            cancel_approval(approval_request, request.user, comments)
            messages.info(request, f'您已撤回代墊款 {payment} 的申請')
        except Exception as e:
            messages.error(request, f'撤回失敗：{str(e)}')
            
    return redirect('administrative:advance_payment_update', pk=pk)
