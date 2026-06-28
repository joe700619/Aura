"""記帳委任書 views：承辦端（清單/草稿/詳情/發送）+ 客戶端公開同意頁。"""
import base64

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import (
    BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin, SortMixin,
)

from ..forms import EngagementLetterForm
from ..models import EngagementLetter, EngagementLetterTemplate
from ..services.engagement_letter import (
    decline_letter, render_letter_html, sign_letter,
)

INVITE_TEMPLATE_CODE = 'bookkeeping_engagement_letter_invite'


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _decode_signature(data_url):
    """把前端 signature_pad 的 dataURL（data:image/png;base64,xxx）解成 bytes。"""
    if not data_url or ',' not in data_url:
        return None
    try:
        return base64.b64decode(data_url.split(',', 1)[1])
    except (ValueError, TypeError):
        return None


class EngagementLetterListView(FilterMixin, ListActionMixin, SearchMixin,
                               SortMixin, BusinessRequiredMixin, ListView):
    model = EngagementLetter
    template_name = 'bookkeeping/engagement_letter/list.html'
    context_object_name = 'letters'
    create_button_label = '新增記帳委任書'
    search_fields = ['company_name', 'tax_id', 'contact_name']
    allowed_sort_fields = ['company_name', 'status', 'engagement_start_date', 'created_at']
    paginate_by = 25
    default_filter = 'all'
    filter_choices = {
        'all': {},
        'draft': {'status': 'draft'},
        'sent': {'status': 'sent'},
        'signed': {'status': 'signed'},
        'declined': {'status': 'declined'},
    }

    def get_base_queryset(self):
        return super().get_base_queryset().select_related(
            'template_version', 'created_client'
        )


class EngagementLetterCreateView(BusinessRequiredMixin, CreateView):
    model = EngagementLetter
    form_class = EngagementLetterForm
    template_name = 'bookkeeping/engagement_letter/form.html'

    def get_success_url(self):
        return reverse('bookkeeping:engagement_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        active = EngagementLetterTemplate.get_active()
        if not active:
            messages.error(self.request, '尚無「使用中」的委任書範本，請先到後台建立並啟用一個版本。')
            return self.render_to_response(self.get_context_data(form=form))
        form.instance.template_version = active
        messages.success(self.request, '委任書草稿已建立，確認內容後即可發送。')
        return super().form_valid(form)


class EngagementLetterUpdateView(BusinessRequiredMixin, UpdateView):
    model = EngagementLetter
    form_class = EngagementLetterForm
    template_name = 'bookkeeping/engagement_letter/form.html'

    def get_queryset(self):
        # 已寄出/已簽的不可再改內容（版本控制紀律）
        return super().get_queryset().filter(status=EngagementLetter.Status.DRAFT)

    def get_success_url(self):
        return reverse('bookkeeping:engagement_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, '委任書已更新。')
        return super().form_valid(form)


class EngagementLetterDetailView(BusinessRequiredMixin, DetailView):
    model = EngagementLetter
    template_name = 'bookkeeping/engagement_letter/detail.html'
    context_object_name = 'letter'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        letter = self.object
        # 已簽看凍結快照；未簽看即時預覽
        ctx['rendered'] = letter.rendered_snapshot or render_letter_html(letter)
        ctx['public_url'] = self.request.build_absolute_uri(
            reverse('bookkeeping:engagement_public', kwargs={'token': letter.token})
        )
        ctx['send_records'] = self._delivery_records(letter)
        return ctx

    @staticmethod
    def _delivery_records(letter):
        """撈這封委任書寄給客戶的 EmailLog（送達/失敗），作為「已送達」證據。

        以收件人 + 邀請範本就近比對既有 EmailLog，依時間新到舊；重發會有多筆。
        """
        if not letter.contact_email:
            return []
        from core.notifications.models import EmailLog
        return list(
            EmailLog.objects.filter(
                recipient=letter.contact_email,
                template__code=INVITE_TEMPLATE_CODE,
            ).order_by('-created_at').values('recipient', 'status', 'created_at')[:20]
        )


class EngagementLetterSendView(BusinessRequiredMixin, View):
    """發送：產生公開連結、寄 email 給客戶、狀態轉已寄出。"""

    def post(self, request, pk):
        letter = get_object_or_404(EngagementLetter, pk=pk)
        if letter.status not in (EngagementLetter.Status.DRAFT,
                                 EngagementLetter.Status.SENT):
            messages.error(request, '此委任書已簽署或婉拒，無法重新發送。')
            return redirect('bookkeeping:engagement_detail', pk=pk)

        if not letter.engagement_start_date:
            messages.error(request, '請先填寫「開始委任日期」再發送（結案自動產生的草稿此欄為空）。')
            return redirect('bookkeeping:engagement_detail', pk=pk)

        public_url = request.build_absolute_uri(
            reverse('bookkeeping:engagement_public', kwargs={'token': letter.token})
        )
        if letter.contact_email:
            from core.notifications.services import EmailService
            EmailService.send_email(
                'bookkeeping_engagement_letter_invite',
                [letter.contact_email],
                {
                    'company_name': letter.company_name,
                    'contact_name': letter.contact_name,
                    'public_url': public_url,
                },
            )
            msg = f'已寄出委任書連結至 {letter.contact_email}。'
        else:
            msg = '已產生委任書連結（未填 Email，請手動把連結傳給客戶）。'

        letter.status = EngagementLetter.Status.SENT
        if not letter.sent_at:
            letter.sent_at = timezone.now()
        letter.save(update_fields=['status', 'sent_at', 'updated_at'])
        messages.success(request, msg)
        return redirect('bookkeeping:engagement_detail', pk=pk)


class EngagementLetterDeleteView(BusinessRequiredMixin, View):
    """軟刪委任書（form_view 工具列的刪除入口；已簽署者保留不刪）。"""

    def get(self, request, pk):
        obj = get_object_or_404(EngagementLetter, pk=pk, is_deleted=False)
        return render(request, 'components/confirm_delete.html', {'object': obj})

    def post(self, request, pk):
        obj = get_object_or_404(EngagementLetter, pk=pk, is_deleted=False)
        obj.is_deleted = True
        obj.save(update_fields=['is_deleted', 'updated_at'])
        messages.success(request, '委任書已刪除。')
        return redirect('bookkeeping:engagement_list')


@method_decorator(xframe_options_sameorigin, name='dispatch')
class EngagementLetterPublicView(View):
    """客戶端免登入同意頁（token）。單一頁面 public.html 處理三態：
    待簽顯示同意/婉拒、已簽顯示確認 banner、已婉拒顯示結尾。

    xframe_options_sameorigin：允許承辦詳情頁以同源 iframe 內嵌預覽
    （覆蓋全站預設 X-Frame-Options: DENY，僅放行同源）。"""

    def _render(self, request, letter):
        # 已簽看凍結快照（所見即所簽）；未簽即時渲染。
        rendered = letter.rendered_snapshot or render_letter_html(letter)
        return render(request, 'bookkeeping/engagement_letter/public.html', {
            'letter': letter,
            'rendered': rendered,
            'preview': request.GET.get('preview') == '1',
        })

    def get(self, request, token):
        letter = get_object_or_404(EngagementLetter, token=token)
        return self._render(request, letter)

    def post(self, request, token):
        letter = get_object_or_404(EngagementLetter, token=token)
        action = request.POST.get('action')
        if letter.status in (EngagementLetter.Status.SIGNED,
                             EngagementLetter.Status.DECLINED):
            return self._render(request, letter)

        if action == 'decline':
            decline_letter(letter, reason=request.POST.get('reason', ''))
            return self._render(request, letter)

        if action == 'agree':
            signer_name = request.POST.get('signer_name', '').strip()
            signer_email = request.POST.get('signer_email', '').strip()
            sig_bytes = _decode_signature(request.POST.get('signature', ''))
            if not signer_name:
                messages.error(request, '請填寫簽署人姓名。')
                return self._render(request, letter)
            if not sig_bytes:
                messages.error(request, '請先手寫簽名後再送出。')
                return self._render(request, letter)
            sign_letter(
                letter, ip=_client_ip(request),
                signature_file=sig_bytes,
                signer_name=signer_name,
                signer_email=signer_email,
            )
            letter.refresh_from_db()
            self._send_receipt(request, letter)

        return self._render(request, letter)

    def _send_receipt(self, request, letter):
        """簽署完成後寄確認回執到客戶信箱：對方信箱也留一份『已於 X 同意委任』，
        強化歸屬證據並提示「若非本人請聯繫」。"""
        email_to = letter.signer_email or letter.contact_email
        if not email_to:
            return
        public_url = request.build_absolute_uri(
            reverse('bookkeeping:engagement_public', kwargs={'token': letter.token})
        )
        ctx = {
            'company_name': letter.company_name,
            'signer_name': letter.signer_name,
            'signed_at': letter.signed_at,
            'firm_name': letter.get_firm_name_display(),
            'public_url': public_url,
        }
        from core.notifications.services import EmailService
        transaction.on_commit(
            lambda: EmailService.send_email(
                'bookkeeping_engagement_letter_receipt', [email_to], ctx)
        )
