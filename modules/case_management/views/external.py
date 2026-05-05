"""外部使用者 magic link 存取 views（免登入）"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from ..models import CaseAccessToken, CaseReply, CaseAttachment
from ..services import annotate_reply_display


def _validate_token(token_str):
    token = get_object_or_404(CaseAccessToken, token=token_str, is_deleted=False)
    if not token.is_valid:
        raise Http404('連結已過期或已撤銷')
    return token


class ExternalCaseAccessView(View):
    template_name = 'case_management/external/case_view.html'

    def get(self, request, token):
        access = _validate_token(token)
        access.mark_used()
        case = access.case
        return render(request, self.template_name, {
            'case': case,
            'access': access,
            'replies': annotate_reply_display(
                list(case.replies.filter(is_deleted=False).order_by('created_at'))
            ),
            'tasks': case.tasks.filter(is_deleted=False, is_hidden=False),
            'attachments': case.attachments.filter(is_deleted=False),
            'token': token,
        })


class ExternalCaseReplyView(View):
    def post(self, request, token):
        access = _validate_token(token)
        content = request.POST.get('content', '').strip()
        files = request.FILES.getlist('files')
        reply = None
        if content or files:
            reply = CaseReply.objects.create(
                case=access.case,
                author_type=CaseReply.AuthorType.EXTERNAL,
                author_display_name=access.email,
                content=content,
                external_channel=CaseReply.Channel.EMAIL,
            )
            for f in files:
                CaseAttachment.objects.create(
                    case=access.case, reply=reply, file=f,
                    original_filename=f.name, size_bytes=f.size,
                    uploaded_by_external_name=access.email,
                )
        if request.headers.get('HX-Request'):
            return render(request, 'case_management/internal/_reply_bubble.html', {'r': reply})
        if reply:
            messages.success(request, '已送出回覆')
        return redirect('case_management:external_access', token=token)
