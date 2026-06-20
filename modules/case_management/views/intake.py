"""商工登記「收料」views。

架構（見 project_commercial_registration_architecture 2026-06-19 段）：
- 收料管道復用 case_management（Case=request_doc + 逐項 CaseTask external + CaseAccessToken MagicLink）。
- 檔案本體**不**落 CaseAttachment，而是走 registration service 建 RegistrationDocument（獨立登記資料庫）。
- 本模組刻意不 import registration model：Case↔Progress 以 ContentType 字串關聯、落檔走 service call，
  維持 case_management 單向不依賴 registration（鐵則）。
"""
import base64

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import View

from modules.registration.services import (
    create_collected_document, remove_collected_document,
    create_beneficial_owner_declaration,
)

from ..models import Case, CaseTask, CaseAccessToken, IntakeDocTypeHelp
from .internal import StaffRequiredMixin
from .external import _validate_token


def _progress_ct():
    """以字串取得 registration.Progress 的 ContentType，避免 import model。"""
    return ContentType.objects.get(app_label='registration', model='progress')


def _collection_cases_for_progress(progress_pk):
    ct = _progress_ct()
    return (
        Case.objects
        .filter(category=Case.Category.REQUEST_DOC,
                client_content_type=ct, client_object_id=progress_pk,
                is_deleted=False)
        .select_related('owner')
        .prefetch_related('tasks__satisfied_by_documents', 'access_tokens')
        .order_by('-created_at')
    )


# ─────────────────────────── 承辦端（內部登入） ───────────────────────────

class IntakeWorkbenchView(StaffRequiredMixin, View):
    """掛在 Progress 詳情頁的「收料」工作台：開收件清單 + 看收料進度。"""
    template_name = 'case_management/internal/intake_workbench.html'

    def get(self, request, progress_pk):
        company = request.GET.get('company', '')
        registration_no = request.GET.get('registration_no', '')
        return render(request, self.template_name, {
            'progress_pk': progress_pk,
            'company': company,
            'registration_no': registration_no,
            'cases': _collection_cases_for_progress(progress_pk),
            'doc_types': CaseTask.CollectedDocType.choices,
        })

    def post(self, request, progress_pk):
        """建立一張收件清單：Case(request_doc) + 逐項 CaseTask(external) + MagicLink。"""
        company = request.POST.get('company', '').strip()
        title = request.POST.get('title', '').strip() or f"登記收件清單 - {company or progress_pk}"
        owner_name = request.POST.get('owner_name', '').strip()
        email = request.POST.get('email', '').strip()

        # 勾選的文件型別 + 各自（可改的）標題
        selected = request.POST.getlist('doc_type')
        valid_types = dict(CaseTask.CollectedDocType.choices)
        selected = [d for d in selected if d in valid_types]
        add_declaration = bool(request.POST.get('add_declaration'))
        if not selected and not add_declaration:
            messages.error(request, '請至少勾選一項要收的文件或聲明書。')
            return redirect(self._workbench_url(progress_pk, company, request.POST.get('registration_no', '')))

        case = Case.objects.create(
            title=title,
            category=Case.Category.REQUEST_DOC,
            status=Case.Status.WAITING_CLIENT,
            source=Case.Source.INTERNAL,
            owner=request.user,
            created_by_user=request.user,
            external_contact_name=owner_name,
            external_contact_email=email,
            client_content_type=_progress_ct(),
            client_object_id=progress_pk,
        )
        for idx, doc_type in enumerate(selected):
            item_title = request.POST.get(f'title_{doc_type}', '').strip() or valid_types[doc_type]
            CaseTask.objects.create(
                case=case, title=item_title,
                assignee_type=CaseTask.Assignee.EXTERNAL,
                target_doc_type=doc_type,
                order=idx,
            )

        # 聲明書項目（客戶填寫+手寫簽署，承辦預填交易內容）
        if add_declaration:
            CaseTask.objects.create(
                case=case,
                title='所有權人/實質受益人聲明書',
                assignee_type=CaseTask.Assignee.EXTERNAL,
                item_kind=CaseTask.ItemKind.DECLARATION,
                target_doc_type=CaseTask.CollectedDocType.OTHER,
                declaration_transaction=request.POST.get('declaration_transaction', '').strip(),
                order=len(selected),
            )

        if email:
            token = CaseAccessToken.issue(case=case, email=email, created_by=request.user)
            link = request.build_absolute_uri(
                reverse('case_management:intake_external', kwargs={'token': token.token})
            )
            messages.success(request, f'收件清單已建立。客戶上傳連結（請複製寄給客戶）：{link}')
        else:
            messages.success(request, '收件清單已建立。請補填客戶 Email 後再產生上傳連結。')

        return redirect(self._workbench_url(progress_pk, company, request.POST.get('registration_no', '')))

    @staticmethod
    def _workbench_url(progress_pk, company='', registration_no=''):
        url = reverse('case_management:intake_workbench', kwargs={'progress_pk': progress_pk})
        from urllib.parse import urlencode
        qs = urlencode({k: v for k, v in {'company': company, 'registration_no': registration_no}.items() if v})
        return f"{url}?{qs}" if qs else url


class IntakeReissueLinkView(StaffRequiredMixin, View):
    """為既有收件清單 Case 重新產生 / 補發 MagicLink。"""
    def post(self, request, pk):
        case = get_object_or_404(
            Case, pk=pk, category=Case.Category.REQUEST_DOC, is_deleted=False
        )
        email = request.POST.get('email', '').strip() or case.external_contact_email
        if not email:
            messages.error(request, '請先填寫客戶 Email。')
        else:
            if email != case.external_contact_email:
                case.external_contact_email = email
                case.save(update_fields=['external_contact_email', 'updated_at'])
            token = CaseAccessToken.issue(case=case, email=email, created_by=request.user)
            link = request.build_absolute_uri(
                reverse('case_management:intake_external', kwargs={'token': token.token})
            )
            messages.success(request, f'已重發上傳連結：{link}')
        return redirect(
            IntakeWorkbenchView._workbench_url(case.client_object_id)
        )


# ─────────────────────────── 客戶端（免登入 token） ───────────────────────────

def _external_tasks(case):
    return (case.tasks
            .filter(assignee_type=CaseTask.Assignee.EXTERNAL, is_deleted=False, is_hidden=False)
            .prefetch_related('satisfied_by_documents')
            .order_by('order', 'created_at'))


def _sync_task_done(task):
    """依「是否還有已上傳文件」同步該項的完成狀態（多檔 + 可刪除後重算）。"""
    has_doc = task.satisfied_by_documents.exists()
    if has_doc and not task.is_done:
        task.mark_done(None)
    elif not has_doc and task.is_done:
        task.is_done = False
        task.done_at = None
        task.done_by = None
        task.save(update_fields=['is_done', 'done_at', 'done_by', 'updated_at'])


def _attach_help(tasks):
    """把每個文件型別的「說明」設定掛到對應 task 上（template 讀 t.help）。"""
    help_map = {h.doc_type: h for h in IntakeDocTypeHelp.objects.filter(is_active=True)}
    for t in tasks:
        t.help = help_map.get(t.target_doc_type)
    return tasks


class ExternalIntakeView(View):
    """客戶端收料清單頁：逐項顯示待上傳 / 已上傳。"""
    template_name = 'case_management/external/intake_view.html'

    def get(self, request, token):
        access = _validate_token(token)
        access.mark_used()
        case = access.case
        tasks = _attach_help(list(_external_tasks(case)))
        return render(request, self.template_name, {
            'case': case, 'access': access, 'token': token,
            'tasks': tasks,
            'all_done': bool(tasks) and all(t.is_done for t in tasks),
        })


class ExternalIntakeUploadView(View):
    """客戶端針對單一項目上傳檔案（可一次多檔）→ 各落一筆 RegistrationDocument 並掛上該項。"""
    def post(self, request, token, task_id):
        access = _validate_token(token)
        case = access.case
        task = get_object_or_404(
            CaseTask, pk=task_id, case=case,
            assignee_type=CaseTask.Assignee.EXTERNAL, is_deleted=False,
        )
        files = request.FILES.getlist('file')
        for f in files:
            document = create_collected_document(
                doc_type=task.target_doc_type or CaseTask.CollectedDocType.OTHER,
                progress=case.client,  # GenericFK 動態解析出 Progress（非 static import）
                file=f,
                owner_name=case.external_contact_name,
                source='client_upload',
                uploaded_by=None,
            )
            task.satisfied_by_documents.add(document)
        if files:
            _sync_task_done(task)

        return self._render_task(request, token, case, task)

    @staticmethod
    def _render_task(request, token, case, task):
        if request.headers.get('HX-Request'):
            tasks = list(_external_tasks(case))
            _attach_help([task])
            return render(request, 'case_management/external/_intake_task.html', {
                'token': token, 't': task,
                'all_done': bool(tasks) and all(t.is_done for t in tasks),
                'oob_submit': True,
            })
        return redirect('case_management:intake_external', token=token)


class ExternalIntakeDeleteFileView(View):
    """客戶端移除某項底下一份已上傳檔案（傳錯時）→ 解除關聯 + 軟刪倉庫文件。"""
    def post(self, request, token, task_id, doc_id):
        access = _validate_token(token)
        case = access.case
        task = get_object_or_404(
            CaseTask, pk=task_id, case=case,
            assignee_type=CaseTask.Assignee.EXTERNAL, is_deleted=False,
        )
        # 僅允許刪除掛在「這一項」底下的文件（避免越權刪倉庫任意檔）
        if task.satisfied_by_documents.filter(pk=doc_id).exists():
            task.satisfied_by_documents.remove(doc_id)
            remove_collected_document(doc_id)  # 走 service 軟刪 registration 端
            _sync_task_done(task)

        return ExternalIntakeUploadView._render_task(request, token, case, task)


def _decode_signature(data_url):
    """把 signature_pad 的 dataURL（data:image/png;base64,...）解成 ContentFile，失敗回 None。"""
    if not data_url or ',' not in data_url:
        return None
    try:
        raw = base64.b64decode(data_url.split(',', 1)[1])
    except Exception:
        return None
    if not raw:
        return None
    return ContentFile(raw, name='signature.png')


class ExternalDeclarationView(View):
    """客戶端：填寫並手寫簽署所有權人/實質受益人聲明書。"""
    template_name = 'case_management/external/declaration_view.html'

    def _get_task(self, case, task_id):
        return get_object_or_404(
            CaseTask, pk=task_id, case=case,
            assignee_type=CaseTask.Assignee.EXTERNAL,
            item_kind=CaseTask.ItemKind.DECLARATION, is_deleted=False,
        )

    def get(self, request, token, task_id):
        access = _validate_token(token)
        access.mark_used()
        case = access.case
        task = self._get_task(case, task_id)
        progress = case.client  # GenericFK → Progress
        return render(request, self.template_name, {
            'token': token, 'case': case, 'task': task, 'access': access,
            'company_name': getattr(progress, 'company_name', '') or '',
            'transaction': task.declaration_transaction,
            'is_signed': task.is_done,
        })


class ExternalDeclarationSubmitView(ExternalDeclarationView):
    """客戶端送出聲明書：產 PDF（走 registration service）→ 掛回該項並標記完成。"""
    def post(self, request, token, task_id):
        access = _validate_token(token)
        case = access.case
        task = self._get_task(case, task_id)

        company_name = request.POST.get('company_name', '').strip()
        transaction = request.POST.get('transaction', '').strip()
        representative_title = request.POST.get('representative_title', '').strip()
        signature_file = _decode_signature(request.POST.get('signature', ''))

        errors = []
        if not company_name:
            errors.append('請填寫本法人名稱。')
        if not representative_title:
            errors.append('請填寫代表人職稱。')
        if signature_file is None:
            errors.append('請手寫簽名後再送出。')
        if errors:
            messages.error(request, ' '.join(errors))
            return redirect('case_management:intake_declaration', token=token, task_id=task_id)

        # 重新簽署 → 取代舊的（聲明書只保留一份有效 PDF）
        for old in task.satisfied_by_documents.all():
            remove_collected_document(old.pk)
        task.satisfied_by_documents.clear()

        document = create_beneficial_owner_declaration(
            progress=case.client,  # GenericFK 動態解析出 Progress
            company_name=company_name,
            transaction_description=transaction,
            representative_title=representative_title,
            signature_file=signature_file,
            signer_email=access.email,
            signer_ip=request.META.get('REMOTE_ADDR'),
        )
        task.satisfied_by_documents.add(document)
        _sync_task_done(task)

        messages.success(request, '聲明書已簽署完成，感謝您。')
        return redirect('case_management:intake_external', token=token)


class ExternalIntakeSubmitView(View):
    """客戶按【送出】：全項到齊才放行 → Case 轉 WAITING_INTERNAL（既有 signal 會通知承辦）。"""
    def post(self, request, token):
        access = _validate_token(token)
        case = access.case
        tasks = list(_external_tasks(case))
        if not tasks or not all(t.is_done for t in tasks):
            messages.error(request, '尚有文件未上傳，請全部上傳後再送出。')
            return redirect('case_management:intake_external', token=token)

        if case.status != Case.Status.WAITING_INTERNAL:
            case.status = Case.Status.WAITING_INTERNAL
            case.save()  # 觸發 notify_on_status_change signal → 通知 Case.owner

        if request.headers.get('HX-Request'):
            return HttpResponse('<div class="cv-done-banner">已送出，我們已通知您的承辦人員，謝謝您！</div>')
        messages.success(request, '已送出，我們已通知承辦人員。')
        return redirect('case_management:intake_external', token=token)
