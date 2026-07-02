"""公司登記委任書 views：

承辦端（工作台 / 產生並發送簽署連結）+ 客戶端免登入簽署頁（簽署或婉拒）。

設計對齊「稿本確認」：進度表分頁只連到本工作台，發送都在獨立頁操作；
內容（條款 + 報價明細）於發送當下凍結，客戶端只讀快照。
"""
import base64
from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from core.mixins import BusinessRequiredMixin

from ..models import Progress, RegistrationMandate, RegistrationMandateTemplate
from ..services import (
    create_registration_mandate,
    decline_registration_mandate,
    remove_paper_mandate,
    render_mandate_html,
    sign_registration_mandate,
    summarize_quotation,
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


def _roc_date_str(d):
    """民國年日期字串（委任書立書日期用）。"""
    return f'中華民國 {d.year - 1911} 年 {d.month} 月 {d.day} 日'


class MandateWorkbenchView(BusinessRequiredMixin, View):
    """承辦端工作台：預覽委任書內容、選通道發送、檢視簽署狀態與發送紀錄。"""

    template_name = 'mandate/workbench.html'

    @staticmethod
    def _match_log(logs, key, value, sent_at):
        """從（依 created_at 升冪的）log 清單挑出對應此次發送的那筆，回傳狀態字串。"""
        if not value or not sent_at:
            return None
        for lg in logs:
            if lg[key] == value and lg['created_at'] >= sent_at - timedelta(seconds=3):
                return lg['status']
        return None

    def _attach_delivery_status(self, records):
        """把通知系統的寄送狀態（已送達/失敗/處理中）掛到每筆發送紀錄上。

        以 recipient + invite 範本 + 時間就近比對既有 EmailLog/LineMessageLog，
        批次兩條 query 比對，避免 N+1。
        """
        from core.notifications.models import EmailLog, LineMessageLog

        emails = [r.recipient_email for r in records if r.recipient_email]
        line_ids = [r.recipient_line_id for r in records if r.recipient_line_id]
        email_logs = list(
            EmailLog.objects.filter(
                recipient__in=emails,
                template__code='registration_mandate_invite',
            ).order_by('created_at').values('recipient', 'status', 'created_at')
        ) if emails else []
        line_logs = list(
            LineMessageLog.objects.filter(
                recipient_line_id__in=line_ids,
                template__code='registration_mandate_invite',
            ).order_by('created_at').values('recipient_line_id', 'status', 'created_at')
        ) if line_ids else []

        for r in records:
            r.email_status = self._match_log(email_logs, 'recipient', r.recipient_email, r.sent_at)
            r.line_status = self._match_log(line_logs, 'recipient_line_id', r.recipient_line_id, r.sent_at)

    def get(self, request, progress_pk):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)
        template = RegistrationMandateTemplate.get_active()

        # 即時預覽：用目前進度表資料渲染（發送時才凍結）
        preview_html = None
        preview_quotation = None
        if template:
            preview_quotation = summarize_quotation(progress.quotation_data)
            preview_html = render_mandate_html(template, progress, preview_quotation)

        active = (
            progress.mandates
            .filter(status=RegistrationMandate.Status.SENT)
            .first()
        )
        send_records = list(progress.mandates.order_by('-created_at')[:50])
        self._attach_delivery_status(send_records)
        latest_signed = (
            progress.mandates
            .filter(status=RegistrationMandate.Status.SIGNED)
            .order_by('-signed_at')
            .first()
        )
        latest_declined = (
            progress.mandates
            .filter(status=RegistrationMandate.Status.DECLINED)
            .order_by('-declined_at')
            .first()
        )
        public_url = None
        if active:
            public_url = request.build_absolute_uri(
                reverse('registration:mandate_public', kwargs={'token': active.token})
            )
        signed_url = None
        if latest_signed:
            signed_url = reverse(
                'registration:mandate_public', kwargs={'token': latest_signed.token}
            )
        from django.utils import timezone
        return render(request, self.template_name, {
            'progress': progress,
            'template': template,
            'doc_date_roc': _roc_date_str(timezone.localtime()),
            'preview_html': preview_html,
            'preview_quotation': preview_quotation,
            'active': active,
            'active_public_url': public_url,
            'latest_signed': latest_signed,
            'signed_url': signed_url,
            'latest_declined': latest_declined,
            'send_records': send_records,
        })


class MandateSendView(BusinessRequiredMixin, View):
    """產生並發送簽署連結：凍結條款與報價快照 → 建 sent 委任書 → 依勾選通道發 LINE/Email。"""

    def post(self, request, progress_pk):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)

        send_email = request.POST.get('channel_email') == 'on'
        send_line = request.POST.get('channel_line') == 'on'
        recipient_email = request.POST.get('recipient_email', '').strip()

        if not send_email and not send_line:
            messages.error(request, '請至少選擇一種通知方式（LINE 或 Email）。')
            return redirect('registration:mandate_workbench', progress_pk=progress.pk)
        if send_email and not recipient_email:
            messages.error(request, '選擇 Email 通知時，請填寫客戶 Email。')
            return redirect('registration:mandate_workbench', progress_pk=progress.pk)

        recipient_line_id = (progress.line_id or progress.room_id or '') if send_line else ''
        if send_line and not recipient_line_id:
            messages.error(request, '此案件未綁定 LINE / Room ID，無法用 LINE 發送。')
            return redirect('registration:mandate_workbench', progress_pk=progress.pk)

        try:
            mandate = create_registration_mandate(
                progress=progress,
                recipient_email=recipient_email,
                recipient_line_id=recipient_line_id,
            )
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('registration:mandate_workbench', progress_pk=progress.pk)

        public_url = request.build_absolute_uri(
            reverse('registration:mandate_public', kwargs={'token': mandate.token})
        )
        ctx = {
            'company_name': progress.company_name,
            'public_url': public_url,
            'expires_at': mandate.expires_at,
        }

        sent_to = []
        if send_email:
            from core.notifications.services import EmailService
            EmailService.send_email('registration_mandate_invite',
                                    [recipient_email], ctx)
            sent_to.append(f'Email（{recipient_email}）')
        if send_line:
            from core.notifications.services import LineService
            # on_commit：等交易 commit 後才推，避免 worker/外部讀到尚未 commit 的紀錄（賽跑）
            transaction.on_commit(
                lambda: LineService.send_message(
                    'registration_mandate_invite', recipient_line_id, ctx)
            )
            sent_to.append('LINE')

        messages.success(request, '已發送委任書簽署連結：' + '、'.join(sent_to) + '。')
        return redirect('registration:mandate_workbench', progress_pk=progress.pk)


class MandatePaperDeleteView(BusinessRequiredMixin, View):
    """移除一份紙本簽回掃描檔（軟刪，傳錯檔時用）。委任狀態不自動回退。

    上傳走進度表主表單（multipart）於儲存時歸檔，見 ProgressCreateView/UpdateView。
    """

    def post(self, request, progress_pk, document_id):
        progress = get_object_or_404(Progress, pk=progress_pk, is_deleted=False)
        doc = remove_paper_mandate(progress, document_id)
        if doc:
            messages.success(request, '已移除一份紙本簽回檔案（委任書簽回狀態未變動，如需調整請在表單修改）。')
        else:
            messages.error(request, '找不到該檔案，可能已被移除。')
        return redirect('registration:progress_edit', pk=progress.pk)


class MandatePublicView(View):
    """客戶端免登入簽署頁（token）。單一頁面處理五態：
    待簽署顯示條款 + 報價明細 + 簽名／婉拒、已簽署顯示完成 banner、
    已婉拒／已作廢／已過期顯示對應提示。
    """

    template_name = 'mandate/public.html'

    def _render(self, request, mandate):
        from django.utils import timezone
        # 立書日期＝發送日（內容凍結時點），非瀏覽當天
        doc_date = timezone.localtime(mandate.sent_at) if mandate.sent_at else timezone.localtime()
        return render(request, self.template_name, {
            'm': mandate,
            'quotation': mandate.quotation_snapshot or {},
            'doc_date_roc': _roc_date_str(doc_date),
        })

    def get(self, request, token):
        mandate = get_object_or_404(RegistrationMandate, token=token)
        return self._render(request, mandate)

    def post(self, request, token):
        mandate = get_object_or_404(RegistrationMandate, token=token)
        if not mandate.is_signable:
            messages.error(request, '此簽署連結已失效，請聯繫承辦人員。')
            return self._render(request, mandate)

        action = request.POST.get('action', 'sign')
        if action == 'decline':
            decline_registration_mandate(
                mandate,
                reason=request.POST.get('decline_reason', '').strip(),
                signer_ip=_client_ip(request),
            )
            return self._render(request, mandate)

        signer_name = request.POST.get('signer_name', '').strip()
        signer_email = request.POST.get('signer_email', '').strip()
        sig_bytes = _decode_signature(request.POST.get('signature', ''))

        if not signer_name:
            messages.error(request, '請填寫簽署人姓名。')
            return self._render(request, mandate)
        if not sig_bytes:
            messages.error(request, '請先手寫簽名後再送出。')
            return self._render(request, mandate)

        sign_registration_mandate(
            mandate,
            signature_file=sig_bytes,
            signer_name=signer_name,
            signer_email=signer_email,
            signer_ip=_client_ip(request),
        )
        mandate.refresh_from_db()
        self._send_receipt(request, mandate)
        return self._render(request, mandate)

    def _send_receipt(self, request, mandate):
        """簽署完成後，把確認回執寄回客戶原本收到連結的管道（Email / LINE）。

        對方信箱/LINE 也留一份「已於 X 簽署」的紀錄，強化歸屬證據；
        回執也提示「若非本人請聯繫」。
        """
        public_url = request.build_absolute_uri(
            reverse('registration:mandate_public', kwargs={'token': mandate.token})
        )
        ctx = {
            'company_name': mandate.progress.company_name,
            'signer_name': mandate.signer_name,
            'signed_at': mandate.signed_at,
            'public_url': public_url,
        }
        email_to = mandate.recipient_email or mandate.signer_email
        if email_to:
            from core.notifications.services import EmailService
            EmailService.send_email(
                'registration_mandate_receipt', [email_to], ctx)
        if mandate.recipient_line_id:
            from core.notifications.services import LineService
            line_id = mandate.recipient_line_id
            transaction.on_commit(
                lambda: LineService.send_message(
                    'registration_mandate_receipt', line_id, ctx)
            )
