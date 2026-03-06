from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from core.mixins import ListActionMixin
from ..models import DocumentDispatch, DocumentDispatchItem, DocumentDispatchImage
from ..forms import DocumentDispatchForm, DocumentDispatchItemFormSet

class DocumentDispatchListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = DocumentDispatch
    template_name = 'administrative/document_dispatch/list.html'
    context_object_name = 'dispatches'
    create_button_label = '新增發文'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '發文紀錄與管理'
        context['breadcrumb'] = [
            {'title': '行政管理', 'url': '#'},
            {'title': '發文系統', 'url': ''},
        ]
        return context

class DocumentDispatchItemListView(LoginRequiredMixin, ListActionMixin, ListView):
    model = DocumentDispatchItem
    template_name = 'administrative/document_dispatch/item_list.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        return super().get_queryset().select_related('dispatch', 'customer').order_by('-dispatch__date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '發文紀錄查詢'
        context['breadcrumb'] = [
            {'title': '發文系統', 'url': reverse_lazy('administrative:document_dispatch_list')},
            {'title': '發文紀錄查詢', 'url': ''},
        ]
        return context

class DocumentDispatchCreateView(LoginRequiredMixin, CreateView):
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

class DocumentDispatchUpdateView(LoginRequiredMixin, UpdateView):
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

class DocumentDispatchDeleteView(LoginRequiredMixin, DeleteView):
    model = DocumentDispatch
    template_name = 'administrative/document_dispatch/confirm_delete.html'
    success_url = reverse_lazy('administrative:document_dispatch_list')

    def form_valid(self, form):
        messages.success(self.request, '發文紀錄已成功刪除。')
        return super().form_valid(form)
