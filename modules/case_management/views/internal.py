"""內部（會計師事務所員工）案件管理 views"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, View

from ..forms import CaseInternalCreateForm
from ..models import (
    Case, CaseTask, CaseReply, CaseAttachment, CaseAccessToken,
)
from ..services import annotate_reply_display


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, 'role', None) == 'EXTERNAL':
            return redirect('client_portal:dashboard')
        return super().dispatch(request, *args, **kwargs)


class InternalCaseListView(StaffRequiredMixin, ListView):
    model = Case
    template_name = 'case_management/internal/case_list.html'
    context_object_name = 'cases'
    paginate_by = 20

    def get_queryset(self):
        qs = Case.objects.filter(is_deleted=False).select_related('owner')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        owner = self.request.GET.get('owner')
        if owner == 'me':
            qs = qs.filter(owner=self.request.user)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search))
        return qs.annotate(reply_count=Count('replies'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Case.Status.choices
        ctx['active_status'] = self.request.GET.get('status', '')
        ctx['active_owner'] = self.request.GET.get('owner', '')
        ctx['search_q'] = self.request.GET.get('q', '')
        return ctx


class InternalCaseDetailView(StaffRequiredMixin, DetailView):
    model = Case
    template_name = 'case_management/internal/case_detail.html'
    context_object_name = 'case'

    def get_queryset(self):
        return Case.objects.filter(is_deleted=False).select_related('owner').prefetch_related(
            'collaborators', 'replies__author_user', 'tasks', 'attachments'
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        case = self.object
        ctx['replies'] = annotate_reply_display(
            list(case.replies.filter(is_deleted=False).order_by('created_at'))
        )
        ctx['tasks'] = case.tasks.filter(is_deleted=False, is_hidden=False).order_by('order', 'created_at')
        ctx['attachments'] = case.attachments.filter(is_deleted=False)
        ctx['status_choices'] = Case.Status.choices
        return ctx


class InternalCaseCreateView(StaffRequiredMixin, CreateView):
    model = Case
    form_class = CaseInternalCreateForm
    template_name = 'case_management/internal/case_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['owner'] = self.request.user
        initial['target_type'] = CaseInternalCreateForm.TARGET_CLIENT
        return initial

    def form_valid(self, form):
        from django.contrib.contenttypes.models import ContentType

        instance = form.instance
        instance.created_by_user = self.request.user
        instance.source = Case.Source.INTERNAL

        if form.cleaned_data.get('target_type') == CaseInternalCreateForm.TARGET_CLIENT:
            bc = form.cleaned_data['bookkeeping_client']
            instance.external_contact_name = bc.contact_person or bc.name
            instance.external_contact_email = bc.email or ''
            instance.external_contact_phone = bc.mobile or bc.phone or ''
            instance.client_content_type = ContentType.objects.get_for_model(type(bc))
            instance.client_object_id = bc.pk
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, '案件已建立')
        return reverse('case_management:internal_detail', kwargs={'pk': self.object.pk})


class InternalCaseReplyView(StaffRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk, is_deleted=False)
        content = request.POST.get('content', '').strip()
        files = request.FILES.getlist('files')
        reply = None
        if content or files:
            reply = CaseReply.objects.create(
                case=case,
                author_type=CaseReply.AuthorType.INTERNAL,
                author_user=request.user,
                author_display_name=request.user.get_full_name() or request.user.username,
                content=content,
                external_channel=CaseReply.Channel.WEB,
            )
            for f in files:
                CaseAttachment.objects.create(
                    case=case, reply=reply, file=f,
                    original_filename=f.name, size_bytes=f.size,
                    uploaded_by_user=request.user,
                )
        if request.headers.get('HX-Request'):
            return render(request, 'case_management/internal/_reply_bubble.html', {'r': reply})
        if reply:
            messages.success(request, '已送出回覆')
        return redirect('case_management:internal_detail', pk=pk)


class InternalCaseTaskAddView(StaffRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk, is_deleted=False)
        title = request.POST.get('title', '').strip()
        assignee = request.POST.get('assignee_type', CaseTask.Assignee.INTERNAL)
        if title:
            task = CaseTask.objects.create(
                case=case, title=title,
                assignee_type=assignee,
                order=case.tasks.count(),
            )
            if request.headers.get('HX-Request'):
                return render(request, 'case_management/internal/_task_item.html', {'t': task})
        return redirect('case_management:internal_detail', pk=pk)


class InternalCaseTaskToggleView(StaffRequiredMixin, View):
    def post(self, request, pk, task_id):
        task = get_object_or_404(CaseTask, pk=task_id, case_id=pk, is_deleted=False)
        if task.is_done:
            task.is_done = False
            task.done_at = None
            task.done_by = None
            task.save(update_fields=['is_done', 'done_at', 'done_by', 'updated_at'])
        else:
            task.mark_done(request.user)
        if request.headers.get('HX-Request'):
            return render(request, 'case_management/internal/_task_item.html', {'t': task})
        return redirect('case_management:internal_detail', pk=pk)


class InternalCaseTaskHideView(StaffRequiredMixin, View):
    def post(self, request, pk, task_id):
        task = get_object_or_404(CaseTask, pk=task_id, case_id=pk, is_deleted=False)
        task.is_hidden = True
        task.save(update_fields=['is_hidden', 'updated_at'])
        if request.headers.get('HX-Request'):
            return HttpResponse('')
        return redirect('case_management:internal_detail', pk=pk)


class InternalCaseTaskReorderView(StaffRequiredMixin, View):
    def post(self, request, pk):
        ids = request.POST.getlist('task_ids[]') or request.POST.get('task_ids', '').split(',')
        ids = [int(x) for x in ids if x]
        for idx, tid in enumerate(ids):
            CaseTask.objects.filter(pk=tid, case_id=pk, is_deleted=False).update(order=idx)
        return HttpResponse('')


class InternalCaseAttachmentUploadView(StaffRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk, is_deleted=False)
        f = request.FILES.get('file')
        if f:
            CaseAttachment.objects.create(
                case=case, file=f,
                original_filename=f.name,
                size_bytes=f.size,
                uploaded_by_user=request.user,
            )
            messages.success(request, f'已上傳 {f.name}')
        return redirect('case_management:internal_detail', pk=pk)


class InternalCaseStatusUpdateView(StaffRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk, is_deleted=False)
        new_status = request.POST.get('status')
        if new_status in dict(Case.Status.choices):
            case.status = new_status
            if new_status == Case.Status.DONE:
                case.closed_at = timezone.now()
            case.save()
            messages.success(request, '狀態已更新')
        return redirect('case_management:internal_detail', pk=pk)


class InternalCaseIssueMagicLinkView(StaffRequiredMixin, View):
    """產生 magic link 並顯示給會計師（之後串 Email 自動寄送）"""
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk, is_deleted=False)
        email = request.POST.get('email') or case.external_contact_email
        if not email:
            messages.error(request, '請先填寫外部聯絡人 Email')
            return redirect('case_management:internal_detail', pk=pk)
        token = CaseAccessToken.issue(case=case, email=email, created_by=request.user)
        url = request.build_absolute_uri(
            reverse('case_management:external_access', kwargs={'token': token.token})
        )
        messages.success(request, f'Magic link 已產生（請複製寄給客戶）：{url}')
        return redirect('case_management:internal_detail', pk=pk)
