from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, CopyMixin, PrevNextMixin, SoftDeleteMixin, FilterMixin
from ..models import DocumentReceipt, DocumentReceiptAttachment
from ..forms import DocumentReceiptForm
from core.notifications.services import LineService

class DocumentReceiptListView(FilterMixin, ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = DocumentReceipt
    template_name = 'administrative/document_receipt/list.html'
    context_object_name = 'receipts'
    paginate_by = 25
    create_button_label = '新增收文'
    search_fields = ['subject', 'customer__name', 'category']
    filter_choices = {
        'pending':    {'status': '待處理'},
        'processing': {'status': '處理中'},
        'closed':     {'status': '已結案'},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().select_related('customer')

    def _base_qs_for_counts(self):
        return self.model.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '收文系統'
        context['breadcrumb'] = [
            {'title': '行政管理', 'url': '#'},
            {'title': '收文系統', 'url': ''},
        ]
        return context

class DocumentReceiptCreateView(CopyMixin, BusinessRequiredMixin, CreateView):
    model = DocumentReceipt
    form_class = DocumentReceiptForm
    template_name = 'administrative/document_receipt/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attachments'] = []
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            for f in self.request.FILES.getlist('new_attachments'):
                DocumentReceiptAttachment.objects.create(receipt=self.object, file=f)
        messages.success(self.request, '新增收文紀錄成功。')
        return redirect('administrative:document_receipt_update', pk=self.object.pk)

    def get_success_url(self):
        return reverse_lazy('administrative:document_receipt_update', kwargs={'pk': self.object.pk})

class DocumentReceiptUpdateView(PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = DocumentReceipt
    form_class = DocumentReceiptForm
    template_name = 'administrative/document_receipt/form.html'
    prev_next_order_field = 'receipt_date'

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()

            deleted_ids_str = self.request.POST.get('deleted_attachment_ids', '')
            if deleted_ids_str:
                id_list = [i.strip() for i in deleted_ids_str.split(',') if i.strip().isdigit()]
                if id_list:
                    DocumentReceiptAttachment.objects.filter(id__in=id_list, receipt=self.object).delete()

            for f in self.request.FILES.getlist('new_attachments'):
                DocumentReceiptAttachment.objects.create(receipt=self.object, file=f)

        messages.success(self.request, '收文紀錄已成功更新。')
        return redirect('administrative:document_receipt_update', pk=self.object.pk)

    def get_success_url(self):
        return reverse_lazy('administrative:document_receipt_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            context['attachments'] = self.object.attachments.all()
        if self.object and hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or "資料變更",
                })
            context['history'] = history_list
        return context

class DocumentReceiptDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = DocumentReceipt
    template_name = 'administrative/document_receipt/confirm_delete.html'
    success_url = reverse_lazy('administrative:document_receipt_list')

class SendDocumentReceiptLineView(BusinessRequiredMixin, View):
    def post(self, request, pk):
        receipt = get_object_or_404(DocumentReceipt, pk=pk)
        
        # recipient resolution
        recipient_id = getattr(receipt.customer, 'line_id', None)
        if not recipient_id and hasattr(receipt.customer, 'contacts'):
            first_contact = receipt.customer.contacts.first()
            if first_contact:
                recipient_id = getattr(first_contact, 'line_id', None)

        if not recipient_id:
             return JsonResponse({'error': '此客戶尚未設定 Line ID，無法發送通知'}, status=400)

        # Build message directly instead of using template to keep it simple as requested
        date_str = receipt.receipt_date.strftime('%Y-%m-%d')
        message = f"親愛的 {receipt.customer.name} 您好：\n我們已於 {date_str} 收到您的信件/物件：{receipt.subject}。\n若有需要後續處理的事項，我們將盡快為您服務，謝謝！"
        
        # Use existing LineService to send raw message if supported. 
        from linebot.models import TextSendMessage
        try:
            line_bot_api = LineService._get_line_bot_api()
            line_bot_api.push_message(recipient_id, TextSendMessage(text=message))
            
            # Update status
            receipt.is_line_notified = True
            receipt.save(update_fields=['is_line_notified'])
            return JsonResponse({'message': 'Line 通知發送成功'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Failed to send Line message: {str(e)}'}, status=500)
