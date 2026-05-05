from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from .services import search_similar
from .models import KnowledgeEntry


class KnowledgeBaseView(LoginRequiredMixin, TemplateView):
    """合併搜尋 + 審核管理的知識庫主頁"""
    template_name = 'knowledge_base/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'search')
        is_staff = self.request.user.is_staff or self.request.user.is_superuser
        ctx['tab'] = tab
        ctx['is_staff'] = is_staff
        ctx['category_choices'] = KnowledgeEntry.Category.choices

        # 搜尋 tab
        query = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip() or None
        ctx['query'] = query
        ctx['category'] = category
        ctx['results'] = []
        ctx['error'] = None
        if tab == 'search' and query:
            try:
                ctx['results'] = search_similar(query, category=category, verified_only=False)
            except Exception as e:
                ctx['error'] = str(e)

        # 審核 tab（僅 staff）
        if is_staff and tab in ('pending', 'verified'):
            qs = KnowledgeEntry.objects.filter(is_deleted=False).select_related(
                'source_case', 'created_by', 'verified_by'
            )
            if category:
                qs = qs.filter(category=category)
            ctx['pending_count'] = qs.filter(is_verified=False).count()
            if tab == 'pending':
                ctx['entries'] = qs.filter(is_verified=False).order_by('-created_at')
            else:
                ctx['entries'] = qs.filter(is_verified=True).order_by('-verified_at')
        else:
            ctx['pending_count'] = KnowledgeEntry.objects.filter(
                is_deleted=False, is_verified=False
            ).count() if is_staff else 0

        return ctx


class KnowledgeSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'knowledge_base/search.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip() or None
        ctx['query'] = query
        ctx['category'] = category
        ctx['category_choices'] = KnowledgeEntry.Category.choices
        ctx['results'] = []
        ctx['error'] = None

        if query:
            try:
                ctx['results'] = search_similar(
                    query,
                    category=category,
                    verified_only=False,
                )
            except Exception as e:
                ctx['error'] = str(e)

        return ctx


class KnowledgeReviewListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """審核管理列表 — 僅 superuser 或 staff"""
    template_name = 'knowledge_base/review_list.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'pending')
        category = self.request.GET.get('category', '').strip() or None

        qs = KnowledgeEntry.objects.filter(is_deleted=False).select_related(
            'source_case', 'created_by', 'verified_by'
        )
        if category:
            qs = qs.filter(category=category)

        ctx['tab'] = tab
        ctx['category'] = category
        ctx['category_choices'] = KnowledgeEntry.Category.choices
        ctx['pending_entries'] = qs.filter(is_verified=False).order_by('-created_at')
        ctx['verified_entries'] = qs.filter(is_verified=True).order_by('-verified_at')
        ctx['pending_count'] = qs.filter(is_verified=False).count()
        return ctx


class KnowledgeReviewActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """approve / reject / edit 單一條目"""

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk):
        entry = get_object_or_404(KnowledgeEntry, pk=pk, is_deleted=False)
        action = request.POST.get('action')

        if action == 'approve':
            entry.is_verified = True
            entry.verified_by = request.user
            entry.verified_at = timezone.now()
            entry.save(update_fields=['is_verified', 'verified_by', 'verified_at', 'updated_at'])
            messages.success(request, f'已審核通過：{entry.question_summary[:40]}')

        elif action == 'reject':
            entry.is_deleted = True
            entry.save(update_fields=['is_deleted', 'updated_at'])
            messages.success(request, '已刪除該條目')

        elif action == 'edit':
            q = request.POST.get('question_summary', '').strip()
            a = request.POST.get('answer_summary', '').strip()
            checklist = request.POST.get('checklist', '').strip()
            category = request.POST.get('category', entry.category)
            visibility = request.POST.get('visibility', entry.visibility)
            valid_until = request.POST.get('valid_until', '') or None

            if not q or not a:
                messages.error(request, '問題與解答不可為空')
                return redirect(reverse('knowledge_base:review_list'))

            entry.question_summary = q
            entry.answer_summary = a
            entry.checklist = checklist
            entry.category = category
            entry.visibility = visibility
            entry.valid_until = valid_until
            update_fields = ['question_summary', 'answer_summary', 'checklist',
                             'category', 'visibility', 'valid_until', 'updated_at']

            # 內容有變動時重新產生 embedding
            try:
                from core.services.embedding import get_embedding
                entry.embedding = get_embedding(f"{q}\n{a}")
                entry.embedding_model = 'gemini-embedding-001'
                entry.embedding_updated_at = timezone.now()
                update_fields += ['embedding', 'embedding_model', 'embedding_updated_at']
            except Exception:
                pass

            entry.save(update_fields=update_fields)
            messages.success(request, '已儲存變更')

        return redirect(reverse('knowledge_base:index') + f'?tab={request.POST.get("return_tab", "pending")}')


class KnowledgeExtractView(LoginRequiredMixin, TemplateView):
    """從案件擷取知識條目 — GET 顯示預填表單，POST 儲存"""
    template_name = 'knowledge_base/extract_form.html'

    def _get_case(self, pk):
        from modules.case_management.models import Case
        return get_object_or_404(Case, pk=pk, is_deleted=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        case = self._get_case(self.kwargs['case_pk'])
        ctx['case'] = case
        ctx['category_choices'] = KnowledgeEntry.Category.choices
        ctx['visibility_choices'] = KnowledgeEntry.Visibility.choices

        # Gemini 自動摘要；失敗時退回標題+摘要
        ai_error = None
        try:
            from core.services.gemini import summarize_case_for_kb
            summary = summarize_case_for_kb(case)
            question_summary = summary['question_summary']
            answer_summary = summary['answer_summary']
        except Exception as e:
            ai_error = str(e)
            question_summary = case.title
            answer_summary = case.summary or ''

        ctx['ai_error'] = ai_error
        ai_category = summary.get('category', 'other') if not ai_error else 'other'
        ctx['prefill'] = {
            'question_summary': question_summary,
            'answer_summary': answer_summary,
            'checklist': summary.get('checklist', '') if not ai_error else '',
            'category': ai_category if ai_category in dict(KnowledgeEntry.Category.choices) else 'other',
            'visibility': 'internal',
        }
        return ctx

    def post(self, request, case_pk):
        case = self._get_case(case_pk)
        q = request.POST.get('question_summary', '').strip()
        a = request.POST.get('answer_summary', '').strip()
        checklist = request.POST.get('checklist', '').strip()
        category = request.POST.get('category', 'other')
        visibility = request.POST.get('visibility', 'internal')

        if not q or not a:
            messages.error(request, '問題與解答均不可為空')
            return redirect(request.path)

        entry = KnowledgeEntry.objects.create(
            question_summary=q,
            answer_summary=a,
            checklist=checklist,
            category=category,
            visibility=visibility,
            source_case=case,
            created_by=request.user,
        )

        try:
            from core.services.embedding import get_embedding
            entry.embedding = get_embedding(f"{q}\n{a}")
            entry.embedding_model = 'gemini-embedding-001'
            entry.embedding_updated_at = timezone.now()
            entry.save(update_fields=['embedding', 'embedding_model', 'embedding_updated_at', 'updated_at'])
        except Exception:
            pass

        messages.success(request, f'已擷取為知識條目（id={entry.pk}），可至知識庫審核後發布')
        return redirect(reverse('case_management:internal_detail', kwargs={'pk': case_pk}))


class KnowledgeApplyChecklistView(LoginRequiredMixin, View):
    """HTMX：批次將知識條目的清單新增為案件待辦"""

    def post(self, request, case_pk):
        from modules.case_management.models import Case, CaseTask
        from django.template.loader import render_to_string

        case = get_object_or_404(Case, pk=case_pk, is_deleted=False)
        checklist_text = request.POST.get('checklist', '')
        assignee = request.POST.get('assignee_type', CaseTask.Assignee.INTERNAL)

        lines = [l.strip() for l in checklist_text.splitlines() if l.strip()]
        if not lines:
            return HttpResponse('')

        base_order = case.tasks.count()
        tasks = CaseTask.objects.bulk_create([
            CaseTask(case=case, title=line, assignee_type=assignee, order=base_order + i)
            for i, line in enumerate(lines)
        ])

        html = ''.join(
            render_to_string('case_management/internal/_task_item.html', {'t': t}, request=request)
            for t in tasks
        )
        return HttpResponse(html)


class KnowledgeSuggestView(LoginRequiredMixin, TemplateView):
    """HTMX partial：依案件標題 + 摘要搜尋相似知識條目"""
    template_name = 'knowledge_base/_kb_suggestions.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from modules.case_management.models import Case
        case = get_object_or_404(Case, pk=self.kwargs['case_pk'], is_deleted=False)

        results = []
        error = None
        # 只有當案件有足夠內容時才搜尋（避免測試/空案件帶出不相關結果）
        has_content = bool(case.summary) or case.replies.filter(
            is_deleted=False, is_system_log=False
        ).exists()

        if has_content:
            query = ' '.join(filter(None, [case.title, case.summary or '']))
            try:
                results = search_similar(
                    query, verified_only=True, top_k=3, threshold=0.4
                )
                # 排除來自本案件自身的條目
                results = [r for r in results if r['entry'].source_case_id != case.pk]
            except Exception as e:
                error = str(e)

        ctx['case'] = case
        ctx['results'] = results
        ctx['error'] = error
        return ctx
