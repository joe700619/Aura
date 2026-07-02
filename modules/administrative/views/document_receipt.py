from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, CopyMixin, PrevNextMixin, SoftDeleteMixin, FilterMixin
from ..models import DocumentReceipt, DocumentReceiptAttachment
from ..forms import DocumentReceiptForm

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
        context['category_default_subjects'] = DocumentReceipt.CATEGORY_DEFAULT_SUBJECTS
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
        context['category_default_subjects'] = DocumentReceipt.CATEGORY_DEFAULT_SUBJECTS
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

