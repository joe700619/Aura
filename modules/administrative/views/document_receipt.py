from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.mixins import ListActionMixin
from ..models import DocumentReceipt
from ..forms import DocumentReceiptForm
from core.notifications.services import LineService

class DocumentReceiptListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = DocumentReceipt
    template_name = 'administrative/document_receipt/list.html'
    context_object_name = 'receipts'
    create_button_label = '新增收文'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '收文系統'
        context['breadcrumb'] = [
            {'title': '行政管理', 'url': '#'},
            {'title': '收文系統', 'url': ''},
        ]
        return context

class DocumentReceiptCreateView(LoginRequiredMixin, CreateView):
    model = DocumentReceipt
    form_class = DocumentReceiptForm
    template_name = 'administrative/document_receipt/form.html'
    success_url = reverse_lazy('administrative:document_receipt_list')

    def form_valid(self, form):
        messages.success(self.request, '新增收文紀錄成功。')
        return super().form_valid(form)

class DocumentReceiptUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DocumentReceipt
    form_class = DocumentReceiptForm
    template_name = 'administrative/document_receipt/form.html'
    success_url = reverse_lazy('administrative:document_receipt_list')
    success_message = "收文紀錄已成功更新"

class DocumentReceiptDeleteView(LoginRequiredMixin, DeleteView):
    model = DocumentReceipt
    template_name = 'administrative/document_receipt/confirm_delete.html'
    success_url = reverse_lazy('administrative:document_receipt_list')

    def form_valid(self, form):
        messages.success(self.request, '收文紀錄已成功刪除。')
        return super().form_valid(form)

class SendDocumentReceiptLineView(LoginRequiredMixin, View):
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
