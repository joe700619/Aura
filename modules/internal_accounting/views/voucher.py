from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import transaction
from django.contrib import messages
from django.utils import timezone

import json
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, SoftDeleteMixin, FilterMixin
from ..models import Voucher, Account, VoucherImage
from ..forms import VoucherForm, VoucherDetailFormSet

class VoucherListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = Voucher
    template_name = 'voucher/list.html'
    context_object_name = 'vouchers'
    paginate_by = 25
    search_fields = ['voucher_no', 'description']
    filter_choices = {
        'DRAFT':  {'status': 'DRAFT'},
        'POSTED': {'status': 'POSTED'},
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '會計傳票列表'
        context['custom_create_url'] = reverse_lazy('internal_accounting:voucher_create')
        context['create_button_label'] = '新增傳票'
        # 便利別名，template 直接用
        context['count_all']    = context['filter_counts']['ALL']
        context['count_draft']  = context['filter_counts']['DRAFT']
        context['count_posted'] = context['filter_counts']['POSTED']
        return context

class VoucherCreateView(BusinessRequiredMixin, CreateView):
    model = Voucher
    form_class = VoucherForm
    template_name = 'voucher/form.html'
    success_url = reverse_lazy('internal_accounting:voucher_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增會計傳票'
        if self.request.POST:
            context['details'] = VoucherDetailFormSet(self.request.POST)
        else:
            context['details'] = VoucherDetailFormSet()
            # Default date to today
            context['form'].initial['date'] = timezone.now().date()
        
        # Pass account auxiliary types for frontend JS to toggle fields
        context['account_aux_types'] = json.dumps(dict(Account.objects.values_list('code', 'auxiliary_type')))
        context['images'] = []
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        details = context['details']
        
        # Auto-generate voucher number if empty
        if not form.cleaned_data.get('voucher_no'):
            today = timezone.now().strftime('%Y%m%d')
            count = Voucher.objects.filter(date=timezone.now().date()).count() + 1
            form.instance.voucher_no = f'VOU-{today}-{count:03d}'

        if details.is_valid():
            # Check balance
            total_debit = sum(d.cleaned_data.get('debit', 0) for d in details.forms if d.cleaned_data and not d.cleaned_data.get('DELETE'))
            total_credit = sum(d.cleaned_data.get('credit', 0) for d in details.forms if d.cleaned_data and not d.cleaned_data.get('DELETE'))
            
            if total_debit != total_credit:
                messages.error(self.request, f"借貸不平衡！借方總額：{total_debit}，貸方總額：{total_credit}")
                return self.form_invalid(form)

            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                details.instance = self.object
                details.save()
                
                # Handle images
                images = self.request.FILES.getlist('images')
                for image in images:
                    VoucherImage.objects.create(voucher=self.object, image=image)
                    
            messages.success(self.request, "傳票已成功新增。")
            return redirect('internal_accounting:voucher_edit', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class VoucherUpdateView(BusinessRequiredMixin, UpdateView):
    model = Voucher
    form_class = VoucherForm
    template_name = 'voucher/form.html'
    success_url = reverse_lazy('internal_accounting:voucher_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯傳票: {self.object.voucher_no}'
        if self.request.POST:
            context['details'] = VoucherDetailFormSet(self.request.POST, instance=self.object)
        else:
            context['details'] = VoucherDetailFormSet(instance=self.object)
            
        context['account_aux_types'] = json.dumps(dict(Account.objects.values_list('code', 'auxiliary_type')))
        
        # Check if period is closed
        from modules.internal_accounting.models.period import AccountingPeriod
        if self.object and self.object.date:
            period = AccountingPeriod.objects.filter(year=self.object.date.year, month=self.object.date.month).first()
            context['is_period_closed'] = period and period.status == AccountingPeriod.Status.CLOSED
        else:
            context['is_period_closed'] = False
        
        # Add images
        context['images'] = self.object.images.all()
        
        # Add history
        context['history'] = self.object.history.select_related('history_user').order_by('-history_date')
        
        # Previous / Next logic using the same ordering as ListView ('-date', '-voucher_no')
        vouchers = list(Voucher.objects.order_by('-date', '-voucher_no'))
        try:
            current_index = vouchers.index(self.object)
            context['prev_object'] = vouchers[current_index - 1] if current_index > 0 else None
            context['next_object'] = vouchers[current_index + 1] if current_index < len(vouchers) - 1 else None
        except ValueError:
            context['prev_object'] = None
            context['next_object'] = None
            
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        details = context['details']
        
        if details.is_valid():
            # Check balance
            total_debit = sum(d.cleaned_data.get('debit', 0) for d in details.forms if d.cleaned_data and not d.cleaned_data.get('DELETE'))
            total_credit = sum(d.cleaned_data.get('credit', 0) for d in details.forms if d.cleaned_data and not d.cleaned_data.get('DELETE'))
            
            if total_debit != total_credit:
                messages.error(self.request, f"借貸不平衡！借方總額：{total_debit}，貸方總額：{total_credit}")
                return self.render_to_response(self.get_context_data(form=form))

            with transaction.atomic():
                self.object = form.save()
                details.instance = self.object
                details.save()
                
                # Handle image deletions
                deleted_ids_str = self.request.POST.get('deleted_image_ids', '')
                if deleted_ids_str:
                    id_list = [id.strip() for id in deleted_ids_str.split(',') if id.strip().isdigit()]
                    if id_list:
                        deleted_count, _ = VoucherImage.objects.filter(id__in=id_list, voucher=self.object).delete()
                        if deleted_count > 0:
                            messages.info(self.request, f"已移除 {deleted_count} 張圖片。")

                # Handle new image uploads
                images = self.request.FILES.getlist('images')
                if images:
                    for image in images:
                        VoucherImage.objects.create(voucher=self.object, image=image)
                    messages.info(self.request, f"已上傳 {len(images)} 張新圖片。")
                    
            messages.success(self.request, "傳票已成功更新。")
            return redirect('internal_accounting:voucher_edit', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class VoucherDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = Voucher
    template_name = 'voucher/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:voucher_list')
