"""商工登記稿本確認 views：

承辦端（工作台 / 上傳稿本 / 刪稿本 / 產生並發送確認連結）+ 客戶端免登入確認簽署頁。

設計對齊既有「收料工作台」：進度表分頁只連到本工作台，所有上傳/發送都在獨立頁操作，
避免塞進進度表主表單造成 nested form。
"""
import base64

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from core.mixins import BusinessRequiredMixin

from ..models import DraftConfirmation, Progress
from ..services import (
    confirm_draft_confirmation,
    create_draft_confirmation,
    create_draft_document,
    list_draft_documents,
    remove_draft_document,
)


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


class DraftConfirmationWorkbenchView(BusinessRequiredMixin, View):
    """承辦端工作台：上傳稿本、勾選用印授權、選通道發送、檢視確認狀態。"""

    template_name = 'draft_confirmation/workbench.html'

    def get(self, request, progress_pk):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)
        documents = list_draft_documents(progress)
        active = (
            progress.draft_confirmations
            .filter(status=DraftConfirmation.Status.SENT)
            .prefetch_related('documents')
            .first()
        )
        history = (
            progress.draft_confirmations
            .exclude(status=DraftConfirmation.Status.SENT)
            .order_by('-created_at')[:20]
        )
        latest_confirmed = (
            progress.draft_confirmations
            .filter(status=DraftConfirmation.Status.CONFIRMED)
            .order_by('-signed_at')
            .first()
        )
        public_url = None
        if active:
            public_url = request.build_absolute_uri(
                reverse('registration:draft_confirm_public', kwargs={'token': active.token})
            )
        confirmed_url = None
        if latest_confirmed:
            confirmed_url = reverse(
                'registration:draft_confirm_public', kwargs={'token': latest_confirmed.token}
            )
        return render(request, self.template_name, {
            'progress': progress,
            'documents': documents,
            'active': active,
            'active_public_url': public_url,
            'latest_confirmed': latest_confirmed,
            'confirmed_url': confirmed_url,
            'history': history,
        })


class DraftDocumentUploadView(BusinessRequiredMixin, View):
    """上傳一份稿本（可一次多檔）。上傳新稿本會作廢既有 active 確認單。"""

    def post(self, request, progress_pk):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)
        files = request.FILES.getlist('files')
        note = request.POST.get('note', '').strip()
        if not files:
            messages.error(request, '請選擇要上傳的稿本檔案。')
            return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)

        for f in files:
            create_draft_document(
                progress=progress, file=f, note=note, uploaded_by=request.user,
            )
        messages.success(request, f'已上傳 {len(files)} 份稿本。')
        return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)


class DraftDocumentDeleteView(BusinessRequiredMixin, View):
    """移除一份稿本（軟刪）。移除也會作廢既有 active 確認單。"""

    def post(self, request, progress_pk, document_id):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)
        doc = remove_draft_document(progress, document_id)
        if doc:
            messages.success(request, '已移除一份稿本。')
        else:
            messages.error(request, '找不到該稿本，可能已被移除。')
        return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)


class DraftConfirmationSendView(BusinessRequiredMixin, View):
    """產生並發送確認連結：凍結稿本清單 → 建 sent 確認單 → 依勾選通道發 LINE/Email。"""

    def post(self, request, progress_pk):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)
        documents = list(list_draft_documents(progress))
        if not documents:
            messages.error(request, '尚未上傳任何稿本，無法發送確認連結。')
            return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)

        send_email = request.POST.get('channel_email') == 'on'
        send_line = request.POST.get('channel_line') == 'on'
        recipient_email = request.POST.get('recipient_email', '').strip()
        seal_authorization = request.POST.get('seal_authorization') == 'on'

        if not send_email and not send_line:
            messages.error(request, '請至少選擇一種通知方式（LINE 或 Email）。')
            return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)
        if send_email and not recipient_email:
            messages.error(request, '選擇 Email 通知時，請填寫客戶 Email。')
            return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)

        recipient_line_id = (progress.line_id or progress.room_id or '') if send_line else ''
        if send_line and not recipient_line_id:
            messages.error(request, '此案件未綁定 LINE / Room ID，無法用 LINE 發送。')
            return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)

        confirmation = create_draft_confirmation(
            progress=progress,
            documents=documents,
            seal_authorization=seal_authorization,
            recipient_email=recipient_email,
            recipient_line_id=recipient_line_id,
        )

        public_url = request.build_absolute_uri(
            reverse('registration:draft_confirm_public', kwargs={'token': confirmation.token})
        )
        ctx = {
            'company_name': progress.company_name,
            'public_url': public_url,
            'expires_at': confirmation.expires_at,
        }

        sent_to = []
        if send_email:
            from core.notifications.services import EmailService
            EmailService.send_email('registration_draft_confirmation_invite',
                                    [recipient_email], ctx)
            sent_to.append(f'Email（{recipient_email}）')
        if send_line:
            from core.notifications.services import LineService
            # on_commit：等交易 commit 後才推，避免 worker/外部讀到尚未 commit 的紀錄（賽跑）
            transaction.on_commit(
                lambda: LineService.send_message(
                    'registration_draft_confirmation_invite', recipient_line_id, ctx)
            )
            sent_to.append('LINE')

        messages.success(request, '已發送稿本確認連結：' + '、'.join(sent_to) + '。')
        return redirect('registration:draft_confirmation_workbench', progress_pk=progress.pk)


class DraftConfirmationPublicView(View):
    """客戶端免登入確認頁（token）。單一頁面處理四態：
    待確認顯示稿本下載 + 簽名、已確認顯示完成 banner、已作廢/已過期顯示對應提示。
    """

    template_name = 'draft_confirmation/public.html'

    def _render(self, request, confirmation):
        # 顯示「發送當下凍結」的完整文件清單，不濾軟刪：簽署即存證，所見即所簽
        # （檔案實體留在 R2 不會消失；日後就算有人軟刪某份，這張紀錄仍呈現當初簽的內容）
        return render(request, self.template_name, {
            'c': confirmation,
            'documents': confirmation.documents.all(),
        })

    def get(self, request, token):
        confirmation = get_object_or_404(DraftConfirmation, token=token)
        return self._render(request, confirmation)

    def post(self, request, token):
        confirmation = get_object_or_404(DraftConfirmation, token=token)
        if not confirmation.is_signable:
            messages.error(request, '此確認連結已失效，請聯繫承辦人員。')
            return self._render(request, confirmation)

        signer_name = request.POST.get('signer_name', '').strip()
        signer_email = request.POST.get('signer_email', '').strip()
        sig_bytes = _decode_signature(request.POST.get('signature', ''))

        if not signer_name:
            messages.error(request, '請填寫簽署人姓名。')
            return self._render(request, confirmation)
        if not sig_bytes:
            messages.error(request, '請先手寫簽名後再送出。')
            return self._render(request, confirmation)

        confirm_draft_confirmation(
            confirmation,
            signature_file=sig_bytes,
            signer_name=signer_name,
            signer_email=signer_email,
            signer_ip=_client_ip(request),
        )
        confirmation.refresh_from_db()
        return self._render(request, confirmation)
