from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, PrevNextMixin, SoftDeleteMixin, FilterMixin
from ..models import DocumentDispatch, DocumentDispatchItem, DocumentDispatchImage
from ..forms import DocumentDispatchForm, DocumentDispatchItemFormSet

class DocumentDispatchListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = DocumentDispatch
    template_name = 'administrative/document_dispatch/list.html'
    context_object_name = 'dispatches'
    paginate_by = 25
    create_button_label = '新增發文'
    search_fields = ['dispatch_method']
    filter_choices = {
        'not_transferred': {'transferred_advance_payment__isnull': True},
        'transferred':     {'transferred_advance_payment__isnull': False},
    }

    def get_base_queryset(self):
        return super().get_base_queryset()

    def _base_qs_for_counts(self):
        return self.model.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '發文紀錄與管理'
        context['breadcrumb'] = [
            {'title': '行政管理', 'url': '#'},
            {'title': '發文系統', 'url': ''},
        ]
        context['model_name'] = 'documentdispatch'
        context['model_app_label'] = 'administrative'
        return context

class DocumentDispatchItemListView(ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = DocumentDispatchItem
    template_name = 'administrative/document_dispatch/item_list.html'
    context_object_name = 'items'
    paginate_by = 25
    search_fields = ['customer__name', 'address', 'contact_person', 'tax_id', 'recipient']

    def get_queryset(self):
        return super().get_queryset().select_related('dispatch', 'customer').order_by('-dispatch__date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '發文紀錄查詢'
        context['breadcrumb'] = [
            {'title': '發文系統', 'url': reverse_lazy('administrative:document_dispatch_list')},
            {'title': '發文紀錄查詢', 'url': ''},
        ]
        context['model_name'] = 'documentdispatchitem'
        context['model_app_label'] = 'administrative'
        return context

class DocumentDispatchCreateView(BusinessRequiredMixin, CreateView):
    model = DocumentDispatch
    form_class = DocumentDispatchForm
    template_name = 'administrative/document_dispatch/form.html'
    success_url = reverse_lazy('administrative:document_dispatch_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增發文紀錄'
        if self.request.POST:
            context['items_formset'] = DocumentDispatchItemFormSet(self.request.POST)
        else:
            context['items_formset'] = DocumentDispatchItemFormSet()
        context['images'] = []
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        
        if items_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                items_formset.instance = self.object
                items_formset.save()
                
                # Handle images
                images = self.request.FILES.getlist('images')
                for image in images:
                    DocumentDispatchImage.objects.create(document=self.object, image=image)
                    
            messages.success(self.request, "發文紀錄已成功新增。")
            return redirect('administrative:document_dispatch_update', pk=self.object.pk)
        else:
            messages.error(self.request, "請修正表格中的錯誤。")
            return self.render_to_response(self.get_context_data(form=form))

class DocumentDispatchUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = DocumentDispatch
    form_class = DocumentDispatchForm
    template_name = 'administrative/document_dispatch/form.html'
    success_url = reverse_lazy('administrative:document_dispatch_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯發文: {self.object.date.strftime("%Y-%m-%d")}'
        if self.request.POST:
            context['items_formset'] = DocumentDispatchItemFormSet(self.request.POST, instance=self.object)
        else:
            context['items_formset'] = DocumentDispatchItemFormSet(instance=self.object)
        context['images'] = self.object.images.all()
        context['history'] = self.object.history.all().order_by('-history_date')[:50]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        
        if items_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                items_formset.instance = self.object
                items_formset.save()
                
                # Handle image deletions
                deleted_ids_str = self.request.POST.get('deleted_image_ids', '')
                if deleted_ids_str:
                    id_list = [img_id.strip() for img_id in deleted_ids_str.split(',') if img_id.strip().isdigit()]
                    if id_list:
                        deleted_count, _ = DocumentDispatchImage.objects.filter(id__in=id_list, document=self.object).delete()
                        if deleted_count > 0:
                            messages.info(self.request, f"已移除 {deleted_count} 張圖片。")

                # Handle new image uploads
                images = self.request.FILES.getlist('images')
                if images:
                    for image in images:
                        DocumentDispatchImage.objects.create(document=self.object, image=image)
                    messages.info(self.request, f"已上傳 {len(images)} 張新圖片。")
                    
            messages.success(self.request, "發文紀錄已成功更新。")
            return redirect('administrative:document_dispatch_update', pk=self.object.pk)
        else:
            messages.error(self.request, "請修正表格中的錯誤。")
            return self.render_to_response(self.get_context_data(form=form))

class DocumentDispatchDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = DocumentDispatch
    template_name = 'administrative/document_dispatch/confirm_delete.html'
    success_url = reverse_lazy('administrative:document_dispatch_list')


@login_required
def document_dispatch_item_label(_request, item_pk):
    """
    Download a .docx mailing label for a single DocumentDispatchItem.
    Template: document_templates/郵寄標籤_範本.docx
    Variables: {{ contact_person }}, {{ customer_name }}, {{ address }}
    """
    import os
    from io import BytesIO
    from docxtpl import DocxTemplate
    from django.conf import settings
    from django.http import HttpResponse

    item = get_object_or_404(DocumentDispatchItem, pk=item_pk)

    template_path = os.path.join(settings.BASE_DIR, 'document_templates', '郵寄標籤_範本.docx')
    doc = DocxTemplate(template_path)
    doc.render({
        'contact_person': item.contact_person or '',
        'customer_name': item.customer.name if item.customer_id else '',
        'address': item.address or '',
    })

    output = BytesIO()
    doc.save(output)
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response['Content-Disposition'] = f'attachment; filename="label_{item.pk}.docx"'
    return response


@login_required
def document_dispatch_transfer_to_advance_payment(request, pk):
    """
    將發文紀錄中「客戶吸收 ✓」的郵資項目，拋轉建立一筆代墊款。
    """
    if request.method != 'POST':
        return redirect('administrative:document_dispatch_update', pk=pk)

    dispatch = get_object_or_404(DocumentDispatch, pk=pk, is_deleted=False)

    if dispatch.transferred_advance_payment_id:
        messages.warning(request, "此發文紀錄已拋轉過代墊款，無法重複操作。")
        return redirect('administrative:document_dispatch_update', pk=pk)

    absorbed_items = dispatch.items.filter(is_absorbed_by_customer=True, postage__gt=0)

    if not absorbed_items.exists():
        messages.warning(request, "沒有勾選「客戶吸收」且郵資大於 0 的項目，無法拋轉。")
        return redirect('administrative:document_dispatch_update', pk=pk)

    from ..models.advance_payment import AdvancePayment, AdvancePaymentDetail

    today = timezone.now().date()
    today_str = today.strftime('%Y%m%d')
    count = AdvancePayment.objects.filter(date=today).count() + 1
    advance_no = f'AP-{today_str}-{count:03d}'

    with transaction.atomic():
        advance = AdvancePayment.objects.create(
            advance_no=advance_no,
            date=today,
            applicant=request.user,
            description=f"發文郵資 {dispatch.date.strftime('%Y-%m-%d')} (發文單 #{dispatch.pk})",
        )
        total = 0
        for item in absorbed_items:
            AdvancePaymentDetail.objects.create(
                advance_payment=advance,
                is_customer_absorbed=True,
                customer=item.customer,
                unified_business_no=item.tax_id or '',
                reason=f"發文郵資（{item.customer.name if item.customer else ''}）",
                amount=item.postage,
                payment_type='POSTAGE',
            )
            total += item.postage
        advance.total_amount = total
        advance.save(update_fields=['total_amount'])
        dispatch.transferred_advance_payment = advance
        dispatch.save(update_fields=['transferred_advance_payment'])

    messages.success(request, f"已成功建立代墊款 {advance_no}，共 {absorbed_items.count()} 筆郵資項目。")
    return redirect('administrative:advance_payment_update', pk=advance.pk)
