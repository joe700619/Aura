import logging
import mimetypes

from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.http import JsonResponse
from core.mixins import BusinessRequiredMixin, ListActionMixin, PrevNextMixin, FilterMixin, SearchMixin, SoftDeleteMixin, SortMixin
from django.contrib import messages
from core.services.gemini import extract_taiwan_id_card
from ..models import Shareholder
from ..forms import ShareholderForm

logger = logging.getLogger(__name__)

class ShareholderListView(SortMixin, FilterMixin, SearchMixin, ListActionMixin, BusinessRequiredMixin, ListView):
    model = Shareholder
    template_name = 'shareholder/list.html'
    context_object_name = 'shareholders'
    paginate_by = 25
    search_fields = ['name', 'id_number']
    default_filter = 'ACTIVE'
    filter_choices = {
        'ACTIVE':   {'is_active': True},
        'INACTIVE': {'is_active': False},
    }
    allowed_sort_fields = ['name', 'id_number', 'nationality', 'birthday', 'is_active']
    default_sort = ['name']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_all']      = context['filter_counts']['ALL']
        context['count_active']   = context['filter_counts']['ACTIVE']
        context['count_inactive'] = context['filter_counts']['INACTIVE']
        return context

class ShareholderCreateView(BusinessRequiredMixin, CreateView):
    model = Shareholder
    form_class = ShareholderForm
    template_name = 'shareholder/form.html'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:shareholder_update', kwargs={'pk': self.object.pk})

class ShareholderUpdateView(BusinessRequiredMixin, PrevNextMixin, UpdateView):
    model = Shareholder
    form_class = ShareholderForm
    template_name = 'shareholder/form.html'
    prev_next_order_field = 'created_at'

    def get_success_url(self):
        messages.success(self.request, '儲存成功！')
        return reverse_lazy('registration:shareholder_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list
        return context

class ShareholderDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = Shareholder
    template_name = 'shareholder/confirm_delete.html'
    success_url = reverse_lazy('registration:shareholder_list')


# 允許的圖片格式（身分證照片）
_ID_CARD_ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'}
_ID_CARD_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class ShareholderIdCardExtractView(BusinessRequiredMixin, View):
    """AI 辨識身分證照片，回傳擷取到的基本資料（不寫入 DB，交前端帶入後由人確認）。

    接收 multipart 的 id_card_front / id_card_back（至少一張），
    直接讀檔 bytes 丟給 Gemini 擷取，不需先存檔。
    """

    def _read_image(self, uploaded):
        if not uploaded:
            return None
        if uploaded.content_type not in _ID_CARD_ALLOWED_MIME:
            raise ValueError(f'不支援的圖片格式：{uploaded.content_type}')
        if uploaded.size > _ID_CARD_MAX_BYTES:
            raise ValueError('圖片過大，請壓縮在 10MB 以內')
        return (uploaded.read(), uploaded.content_type)

    def _read_saved(self, field_file):
        """讀取已存在 storage（R2）的照片，回傳 (bytes, mime) 或 None。"""
        if not field_file:
            return None
        mime = mimetypes.guess_type(field_file.name)[0] or 'image/jpeg'
        with field_file.open('rb') as f:
            return (f.read(), mime)

    def post(self, request):
        try:
            front = self._read_image(request.FILES.get('id_card_front'))
            back = self._read_image(request.FILES.get('id_card_back'))
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

        # 編輯頁：沒重新上傳的那一面，改讀資料庫裡已存的照片
        shareholder_id = request.POST.get('shareholder_id')
        if shareholder_id and (not front or not back):
            obj = Shareholder.objects.filter(pk=shareholder_id, is_deleted=False).first()
            if obj:
                if not front:
                    front = self._read_saved(obj.id_card_front)
                if not back:
                    back = self._read_saved(obj.id_card_back)

        if not front and not back:
            return JsonResponse({'success': False, 'error': '請先上傳身分證照片'}, status=400)

        try:
            data = extract_taiwan_id_card(front=front, back=back)
        except Exception:
            logger.exception('身分證 AI 辨識失敗')
            return JsonResponse({'success': False, 'error': 'AI 辨識失敗，請稍後再試或手動輸入'}, status=502)

        return JsonResponse({'success': True, 'data': data})
