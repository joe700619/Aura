"""記帳委任書 views：承辦端（清單/草稿/詳情/發送）+ 客戶端公開同意頁。"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import (
    BusinessRequiredMixin, FilterMixin, ListActionMixin, SearchMixin, SortMixin,
)

from ..forms import EngagementLetterForm
from ..models import EngagementLetter, EngagementLetterTemplate
from ..services.engagement_letter import (
    decline_letter, render_letter_html, sign_letter,
)


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


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
        return ctx


class EngagementLetterSendView(BusinessRequiredMixin, View):
    """發送：產生公開連結、寄 email 給客戶、狀態轉已寄出。"""

    def post(self, request, pk):
        letter = get_object_or_404(EngagementLetter, pk=pk)
        if letter.status not in (EngagementLetter.Status.DRAFT,
                                 EngagementLetter.Status.SENT):
            messages.error(request, '此委任書已簽署或婉拒，無法重新發送。')
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


class EngagementLetterPublicView(View):
    """客戶端免登入同意頁（token）。GET 看條文、POST 同意/婉拒。"""

    def get(self, request, token):
        letter = get_object_or_404(EngagementLetter, token=token)
        if letter.status == EngagementLetter.Status.SIGNED:
            return render(request, 'bookkeeping/engagement_letter/public_done.html', {
                'letter': letter, 'declined': False,
            })
        if letter.status == EngagementLetter.Status.DECLINED:
            return render(request, 'bookkeeping/engagement_letter/public_done.html', {
                'letter': letter, 'declined': True,
            })
        return render(request, 'bookkeeping/engagement_letter/public.html', {
            'letter': letter,
            'rendered': render_letter_html(letter),
        })

    def post(self, request, token):
        letter = get_object_or_404(EngagementLetter, token=token)
        action = request.POST.get('action')
        if letter.status in (EngagementLetter.Status.SIGNED,
                             EngagementLetter.Status.DECLINED):
            return redirect('bookkeeping:engagement_public', token=token)

        if action == 'agree':
            sign_letter(letter, ip=_client_ip(request))
            return render(request, 'bookkeeping/engagement_letter/public_done.html', {
                'letter': letter, 'declined': False,
            })
        if action == 'decline':
            decline_letter(letter, reason=request.POST.get('reason', ''))
            return render(request, 'bookkeeping/engagement_letter/public_done.html', {
                'letter': letter, 'declined': True,
            })
        return redirect('bookkeeping:engagement_public', token=token)
