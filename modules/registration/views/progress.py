from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from core.mixins import PrevNextMixin
from ..models.progress import Progress
from ..forms import ProgressForm
from django.db.models import Q

class ProgressListView(LoginRequiredMixin, ListView):
    model = Progress
    template_name = 'progress/list.html'
    context_object_name = 'progress_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        search_query = self.request.GET.get('q')

        if status_filter:
            queryset = queryset.filter(progress_status=status_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(registration_no__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(main_contact__icontains=search_query) |
                Q(unified_business_no__icontains=search_query)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_status = self.request.GET.get('status', '')
        
        # Prepare status choices with selection state
        status_options = []
        for value, label in Progress.ProgressStatus.choices:
            status_options.append({
                'value': value,
                'label': label,
                'selected': str(value) == current_status
            })
            
        context['status_options'] = status_options
        
        # Context for list_view.html component
        context['model_name'] = 'registration:progress'
        context['model_app_label'] = 'registration'
        context['create_button_label'] = '新增案件'
        return context

class ProgressCreateView(LoginRequiredMixin, CreateView):
    model = Progress
    form_class = ProgressForm
    template_name = 'progress/form.html'

    def get_success_url(self):
        return reverse_lazy('registration:progress_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增登記進度'
        return context

class ProgressUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = Progress
    form_class = ProgressForm
    template_name = 'progress/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        return reverse_lazy('registration:progress_edit', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        from django.contrib import messages
        
        # Check if is_posted just changed from False to True
        if 'is_posted' in form.changed_data and form.cleaned_data['is_posted']:
            try:
                from modules.internal_accounting.services import ReceivableTransferService
                # 1. AR Transfer (if not already transferred)
                if not self.object.is_ar_transferred:
                    ReceivableTransferService.create_from_source(self.object)
                
                # 2. Voucher Generation
                voucher = ReceivableTransferService.generate_voucher_for_progress(self.object, self.request.user)
                if voucher:
                    messages.success(self.request, f"成功拋轉應收帳款並產生傳票 ({voucher.voucher_no})！")
                else:
                    messages.success(self.request, "成功拋轉應收帳款，但無符合的報價單項目可產生傳票。")
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(self.request, f"拋轉失敗：{str(e)}")
                # Revert is_posted flag on error
                self.object.is_posted = False
                self.object.save(update_fields=['is_posted'])
                
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '編輯登記進度'
        
        from ..models import FilingHistory, CaseAssessment, EquityTransaction, VATEntityChange
        
        # Check if 22-1 is required based on quotation_data
        quotation_data = self.object.quotation_data
        should_have_22_1 = any(
            isinstance(item, dict) and item.get('is_company_law_22_1') is True 
            for item in quotation_data
        ) if isinstance(quotation_data, list) else False

        should_have_aml = any(
            isinstance(item, dict) and item.get('is_money_laundering_check') is True 
            for item in quotation_data
        ) if isinstance(quotation_data, list) else False

        should_have_equity_tx = any(
            isinstance(item, dict) and item.get('is_shareholder_list_change') is True 
            for item in quotation_data
        ) if isinstance(quotation_data, list) else False

        should_have_vat_change = any(
            isinstance(item, dict) and item.get('is_business_entity_change') is True 
            for item in quotation_data
        ) if isinstance(quotation_data, list) else False

        # Search for related records
        related_history = FilingHistory.objects.filter(registration_no=self.object.registration_no).first()
        related_assessment = CaseAssessment.objects.filter(registration_no=self.object.registration_no).first()
        related_tx = EquityTransaction.objects.filter(registration_no=self.object.registration_no).first()
        related_vat = VATEntityChange.objects.filter(registration_no=self.object.registration_no).first()

        context['checklist'] = {
            'company_law_22_1': {
                'required': should_have_22_1,
                'exists': related_history is not None,
                'object': related_history,
                'is_completed': related_history.is_completed if related_history else False,
                'url': reverse_lazy('registration:filing_history_edit', kwargs={'pk': related_history.pk}) if related_history else None,
            },
            'aml_check': {
                'required': should_have_aml,
                'exists': related_assessment is not None,
                'object': related_assessment,
                'is_completed': related_assessment.is_completed if related_assessment else False,
                'url': reverse_lazy('registration:case_assessment_update', kwargs={'pk': related_assessment.pk}) if related_assessment else None,
            },
            'equity_tx': {
                'required': should_have_equity_tx,
                'exists': related_tx is not None,
                'object': related_tx,
                'is_completed': related_tx.is_completed if related_tx else False,
                'url': reverse_lazy('registration:equity_transaction_update', kwargs={'pk': related_tx.pk}) if related_tx else None,
            },
            'vat_change': {
                'required': should_have_vat_change,
                'exists': related_vat is not None,
                'object': related_vat,
                'is_completed': related_vat.is_completed if related_vat else False,
                'url': reverse_lazy('registration:vat_entity_change_update', kwargs={'pk': related_vat.pk}) if related_vat else None,
            }
        }
        return context

class ProgressDeleteView(LoginRequiredMixin, DeleteView):
    model = Progress
    success_url = reverse_lazy('registration:progress_list')
    template_name = 'progress/confirm_delete.html' 

from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from modules.internal_accounting.services import ReceivableTransferService

class PaymentLinkGenerateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        progress = get_object_or_404(Progress, pk=pk)
        
        # Try to save the form data first
        form = ProgressForm(request.POST, instance=progress)
        if form.is_valid():
            form.save()
            messages.success(request, '資料已儲存並生成支付連結')
        else:
            messages.warning(request, '資料驗證失敗，僅生成支付連結 (使用現有資料)')
            # You might want to log form.errors here for debugging
            
        progress.generate_payment_token()
        return redirect('registration:progress_edit', pk=pk)

class ProgressTransferToARView(LoginRequiredMixin, View):
    def post(self, request, pk):
        progress = get_object_or_404(Progress, pk=pk)
        
        if progress.is_ar_transferred:
            messages.warning(request, '此案件已拋轉過應收帳款，請勿重複操作。')
            return redirect('registration:progress_edit', pk=pk)
        
        try:
            receivable = ReceivableTransferService.create_from_source(progress)
            messages.success(request, f'成功拋轉！應收帳款編號：{receivable.receivable_no}')
            return redirect('internal_accounting:receivable_edit', pk=receivable.pk)
        except Exception as e:
            messages.error(request, f'拋轉失敗：{str(e)}')
            return redirect('registration:progress_edit', pk=pk)
