"""客戶端 (client_portal) 案件管理 views"""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView, View

from modules.client_portal.mixins import ClientRequiredMixin

from ..forms import CaseClientCreateForm
from ..models import Case, CaseReply, CaseAttachment, CaseTask, CaseTaskTemplate
from ..services import annotate_reply_display


def _get_client_owner(user):
    """從客戶 profile 推出對應的負責會計師（使用記帳助理 → Employee.user）

    順序：bookkeeping_assistant.user → group_assistant.user → 首位 staff fallback
    """
    from django.contrib.auth import get_user_model

    profile = getattr(user, 'bookkeeping_client_profile', None)
    if profile:
        for emp in (profile.bookkeeping_assistant, profile.group_assistant):
            if emp and getattr(emp, 'user_id', None):
                return emp.user
    User = get_user_model()
    return User.objects.filter(is_staff=True, is_active=True).order_by('id').first()


def _get_client_profile(user):
    """取得客戶的 BookkeepingClient profile（用於案件 GenericFK）"""
    return getattr(user, 'bookkeeping_client_profile', None)


def _client_case_qs(user):
    """限定該客戶可看到的案件

    匹配條件（任一）：
    - 案件由此 user 透過 portal 發起（created_by_user）
    - 案件透過 GenericFK 關聯到此客戶的 BookkeepingClient profile
      （涵蓋會計師代建、未來 LINE/Email 轉入的案件）
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q

    qs = Case.objects.filter(is_deleted=False)
    profile = getattr(user, 'bookkeeping_client_profile', None)
    if profile:
        ct = ContentType.objects.get_for_model(type(profile))
        qs = qs.filter(
            Q(created_by_user=user)
            | Q(client_content_type=ct, client_object_id=profile.pk)
        )
    else:
        qs = qs.filter(created_by_user=user)
    return qs.select_related('owner').distinct()


class PortalCaseListView(ClientRequiredMixin, ListView):
    model = Case
    template_name = 'case_management/portal/case_list.html'
    context_object_name = 'cases'
    paginate_by = 10

    def get_queryset(self):
        qs = _client_case_qs(self.request.user).annotate(
            reply_count=Count('replies', filter=Q(replies__is_system_log=False, replies__is_deleted=False), distinct=True),
            attachment_count=Count('attachments', filter=Q(attachments__is_deleted=False), distinct=True),
        )
        status = self.request.GET.get('status') or 'open'
        if status == 'open':
            qs = qs.exclude(status__in=[Case.Status.DONE, Case.Status.ARCHIVED])
        elif status == 'done':
            qs = qs.filter(status=Case.Status.DONE)
        elif status == 'archived':
            qs = qs.filter(status=Case.Status.ARCHIVED)
        # status == 'all' → no filter
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search))
        return qs.order_by('-last_activity_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        all_cases = _client_case_qs(self.request.user)
        ctx['active_status'] = self.request.GET.get('status') or 'open'
        ctx['search_q'] = self.request.GET.get('q', '').strip()
        ctx['count_open'] = all_cases.exclude(status__in=[Case.Status.DONE, Case.Status.ARCHIVED]).count()
        ctx['count_done'] = all_cases.filter(status=Case.Status.DONE).count()
        ctx['count_archived'] = all_cases.filter(status=Case.Status.ARCHIVED).count()
        ctx['count_all'] = all_cases.count()
        return ctx


class PortalCaseCreateView(ClientRequiredMixin, CreateView):
    model = Case
    form_class = CaseClientCreateForm
    template_name = 'case_management/portal/case_form.html'

    def form_valid(self, form):
        from django.contrib.contenttypes.models import ContentType

        owner = _get_client_owner(self.request.user)
        if owner is None:
            messages.error(self.request, '尚未指派負責會計師，請聯絡事務所')
            return redirect('client_portal:dashboard')
        form.instance.owner = owner
        form.instance.created_by_user = self.request.user
        form.instance.source = Case.Source.CLIENT_PORTAL
        form.instance.external_contact_name = self.request.user.get_full_name() or self.request.user.username
        form.instance.external_contact_email = self.request.user.email

        profile = _get_client_profile(self.request.user)
        if profile:
            form.instance.client_content_type = ContentType.objects.get_for_model(type(profile))
            form.instance.client_object_id = profile.pk
            if not form.instance.external_contact_phone and getattr(profile, 'mobile', None):
                form.instance.external_contact_phone = profile.mobile
        response = super().form_valid(form)
        # 自動帶入該客戶為此類別預定義的清單範本
        if profile:
            templates = CaseTaskTemplate.objects.filter(
                bookkeeping_client=profile,
                category=self.object.category,
                is_deleted=False,
            ).order_by('order', 'created_at')
            CaseTask.objects.bulk_create([
                CaseTask(
                    case=self.object,
                    title=t.title,
                    assignee_type=CaseTask.Assignee.INTERNAL,
                    order=t.order,
                )
                for t in templates
            ])
        return response

    def get_success_url(self):
        messages.success(self.request, '案件已送出，會計師將儘快回覆')
        return reverse('case_portal:detail', kwargs={'pk': self.object.pk})


class PortalCaseDetailView(ClientRequiredMixin, DetailView):
    model = Case
    template_name = 'case_management/portal/case_detail.html'
    context_object_name = 'case'

    def get_queryset(self):
        return _client_case_qs(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        case = self.object
        ctx['replies'] = annotate_reply_display(
            list(case.replies.filter(is_deleted=False).order_by('created_at'))
        )
        ctx['tasks'] = case.tasks.filter(is_deleted=False, is_hidden=False)
        ctx['attachments'] = case.attachments.filter(is_deleted=False)
        return ctx


class PortalCaseReplyView(ClientRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(_client_case_qs(request.user), pk=pk)
        content = request.POST.get('content', '').strip()
        files = request.FILES.getlist('files')
        reply = None
        if content or files:
            reply = CaseReply.objects.create(
                case=case,
                author_type=CaseReply.AuthorType.EXTERNAL,
                author_user=request.user,
                author_display_name=request.user.get_full_name() or request.user.username,
                content=content,
                external_channel=CaseReply.Channel.PORTAL,
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
        return redirect('case_portal:detail', pk=pk)


class PortalChecklistTemplateView(ClientRequiredMixin, View):
    """客戶端 - 案件清單範本管理（GET 顯示 + POST 各種 action）"""

    template_name = 'case_management/portal/checklist_settings.html'

    def _get_profile_or_redirect(self, request):
        profile = _get_client_profile(request.user)
        if not profile:
            messages.error(request, '尚未綁定客戶資料')
            return None
        return profile

    def get(self, request):
        profile = self._get_profile_or_redirect(request)
        if not profile:
            return redirect('client_portal:settings')
        templates = CaseTaskTemplate.objects.filter(
            bookkeeping_client=profile, is_deleted=False,
        ).order_by('category', 'order', 'created_at')
        grouped = {value: [] for value, _ in Case.Category.choices}
        for t in templates:
            grouped.setdefault(t.category, []).append(t)
        ctx = {
            'category_groups': [
                {'value': v, 'label': label, 'items': grouped.get(v, [])}
                for v, label in Case.Category.choices
            ],
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        profile = self._get_profile_or_redirect(request)
        if not profile:
            return redirect('client_portal:settings')
        action = request.POST.get('action')

        if action == 'add':
            category = request.POST.get('category', '').strip()
            title = request.POST.get('title', '').strip()
            valid_cats = {v for v, _ in Case.Category.choices}
            if title and category in valid_cats:
                last = CaseTaskTemplate.objects.filter(
                    bookkeeping_client=profile, category=category, is_deleted=False,
                ).order_by('-order').first()
                next_order = (last.order + 1) if last else 0
                CaseTaskTemplate.objects.create(
                    bookkeeping_client=profile,
                    category=category,
                    title=title[:300],
                    order=next_order,
                )
                messages.success(request, '已新增清單項目')
            else:
                messages.error(request, '請輸入項目內容')

        elif action == 'update':
            tpl = get_object_or_404(
                CaseTaskTemplate, pk=request.POST.get('id'),
                bookkeeping_client=profile, is_deleted=False,
            )
            title = request.POST.get('title', '').strip()
            if title:
                tpl.title = title[:300]
                tpl.save(update_fields=['title', 'updated_at'])
                messages.success(request, '已更新項目')
            else:
                messages.error(request, '項目內容不可為空')

        elif action == 'delete':
            tpl = get_object_or_404(
                CaseTaskTemplate, pk=request.POST.get('id'),
                bookkeeping_client=profile, is_deleted=False,
            )
            tpl.is_deleted = True
            tpl.save(update_fields=['is_deleted', 'updated_at'])
            messages.success(request, '已刪除項目')

        return redirect('case_portal:checklist')
