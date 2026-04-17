from django.db.models import Q
from django.http import HttpResponseRedirect
from django.contrib import messages

class SoftDeleteMixin:
    """
    Mixin for DeleteView to perform a soft delete instead of hard delete.
    Requires the model to have an `is_deleted` boolean field.
    Compatible with Django 4.0+ where DeleteView uses form_valid() instead of delete().
    """
    def get(self, request, *args, **kwargs):
        # Render a confirmation page instead of directly deleting.
        # Avoids Django 5.1 form-binding issue; POST triggers form_valid() below.
        from django.shortcuts import render as _render
        self.object = self.get_object()
        template_names = [
            f'{self.object._meta.app_label}/{self.object._meta.model_name}_confirm_delete.html',
            'components/confirm_delete.html',
        ]
        return _render(request, template_names, {'object': self.object})

    def form_valid(self, _form):
        self.object = self.get_object()
        success_url = self.get_success_url()

        if hasattr(self.object, 'is_deleted'):
            self.object.is_deleted = True
            self.object.save(update_fields=['is_deleted', 'updated_at'])
            messages.success(self.request, f"「{self.object}」已成功刪除（移至資源回收桶）。")
        else:
            # 如果沒有 is_deleted 欄位，退回原始寫法（硬刪除）
            messages.warning(self.request, f"「{self.object}」已永久刪除。")
            self.object.delete()

        return HttpResponseRedirect(success_url)

class PrevNextMixin:
    """
    Mixin to add previous and next object navigation to context.
    Expects `self.object` to be set (UpdateView/DetailView).
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ensure we have an object to navigate from
        if not hasattr(self, 'object') or not self.object:
            return context

        # Use get_queryset() so navigation respects any filtering (e.g. is_deleted=False).
        queryset = self.get_queryset()

        current_pk = self.object.pk

        # Next Object (pk > current_pk, order by pk asc)
        next_obj = queryset.filter(pk__gt=current_pk).order_by('pk').first()
        
        # Previous Object (pk < current_pk, order by pk desc)
        prev_obj = queryset.filter(pk__lt=current_pk).order_by('-pk').first()

        context['next_object'] = next_obj
        context['prev_object'] = prev_obj
        
        return context


class CopyMixin:
    """
    Mixin to handle copying an existing object when creating a new one.
    Expects `?source_id=<pk>` in the URL query parameters.
    
    Usage in CreateView:
        class MyModelCreateView(CopyMixin, CreateView):
            model = MyModel
            fields = [...]
            
            def get_copy_exclude_fields(self):
                # Customize which fields should NOT be copied
                return ['id', 'unique_field', 'created_at']
    """
    
    def get_copy_exclude_fields(self):
        """
        Override this method to specify which fields should be excluded from copying.
        By default, excludes: id, pk, created_at, updated_at, created_by, updated_by
        """
        return ['id', 'pk', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_initial(self):
        """Handle copying data from source object if source_id is provided."""
        initial = super().get_initial()
        source_id = self.request.GET.get('source_id')
        
        if source_id:
            try:
                source_object = self.model.objects.get(pk=source_id)
                exclude_fields = self.get_copy_exclude_fields()
                
                # Copy all fields that are in self.fields (if defined)
                if hasattr(self, 'fields') and self.fields:
                    fields_to_copy = self.fields
                else:
                    # If fields not defined, copy all model fields except excluded
                    fields_to_copy = [f.name for f in self.model._meta.get_fields() 
                                     if not f.many_to_many and not f.one_to_many]
                
                for field_name in fields_to_copy:
                    if field_name not in exclude_fields:
                        try:
                            value = getattr(source_object, field_name, None)
                            if value is not None:
                                initial[field_name] = value
                        except AttributeError:
                            # Skip fields that don't exist on the source object
                            pass
                            
            except self.model.DoesNotExist:
                # Source object not found, proceed normally
                pass
        
        return initial


class HistoryMixin:
    """
    Mixin to add object change history to context for UpdateView.
    Requires the model to have a 'history' field (django-simple-history via BaseModel).
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
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


class SearchMixin:
    """
    Mixin for ListView to support server-side search via ?q= GET parameter.
    Define search_fields as a list of ORM lookup fields (e.g. ['name', 'tax_id']).
    Adds 'q' to context so templates can pre-fill the search input.
    """
    search_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f'{field}__icontains': q})
            qs = qs.filter(query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        return context


class SortMixin:
    """
    Mixin for ListView to support server-side sorting via ?sort= field parameter.
    Define allowed_sort_fields as a list of ORM lookup fields (e.g. ['name', 'tax_id', 'group_assistant__name']).
    Adds 'current_sort' to context.
    """
    allowed_sort_fields = []
    default_sort = ['-created_at']

    def get_ordering(self):
        sort = self.request.GET.get('sort', '').strip()
        if sort:
            # Handle reverse sort (prefix with '-')
            field_to_check = sort.lstrip('-')
            if field_to_check in self.allowed_sort_fields:
                return [sort]
        return getattr(super(), 'get_ordering', lambda: self.default_sort)()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get('sort', '').strip()
        return context


class FilterMixin:
    """
    Mixin for ListView to provide backend status filtering via ?filter= GET parameter.

    Usage:
        class MyListView(FilterMixin, ListActionMixin, ListView):
            model = MyModel
            filter_field = 'status'            # DB field to filter on (default: 'status')
            filter_choices = {                 # mapping: URL param value → ORM filter kwargs
                'DRAFT':  {'status': 'DRAFT'},
                'POSTED': {'status': 'POSTED'},
            }
            # Optional: if status is a Python property (not a DB field), set:
            filter_property = 'status'         # model property name to use for counting

    If filter_property is set, filtering and counting are done in Python (list comprehension).
    Otherwise, ORM .filter(**kwargs) is used.
    """

    filter_field = 'status'
    filter_choices = {}      # subclass must define
    filter_property = None   # set to property name if not a DB field
    default_filter = 'ALL'   # override in subclass to pre-select a filter on first load

    def get_base_queryset(self):
        """
        Return the base queryset BEFORE filter is applied.
        Override in subclass to add is_deleted, prefetch_related, etc.
        This is called by both get_queryset() and _base_qs_for_counts().
        """
        qs = super().get_queryset()
        if hasattr(self.model, 'is_deleted'):
            qs = qs.filter(is_deleted=False)
        return qs

    def _base_qs_for_counts(self):
        """Return a plain (no prefetch) queryset for counting."""
        qs = self.model.objects.all()
        if hasattr(self.model, 'is_deleted'):
            qs = qs.filter(is_deleted=False)
        return qs

    def apply_filter(self, qs):
        """Apply ?filter= to the queryset. Subclass may override for custom logic."""
        f = self.request.GET.get('filter', self.default_filter)
        if f == 'ALL' or f not in self.filter_choices:
            return qs
        filter_kwargs = self.filter_choices[f]
        if self.filter_property:
            # Python-level filtering (for computed properties)
            return [obj for obj in qs if getattr(obj, self.filter_property) == f]
        return qs.filter(**filter_kwargs)

    def get_queryset(self):
        qs = self.get_base_queryset()
        return self.apply_filter(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        f = self.request.GET.get('filter', self.default_filter)
        context['current_filter'] = f

        base = self._base_qs_for_counts()
        counts = {'ALL': 0}

        if self.filter_property:
            all_objs = list(base)
            counts['ALL'] = len(all_objs)
            for key in self.filter_choices:
                counts[key] = sum(
                    1 for obj in all_objs
                    if getattr(obj, self.filter_property) == key
                )
        else:
            counts['ALL'] = base.count()
            for key, filter_kwargs in self.filter_choices.items():
                counts[key] = base.filter(**filter_kwargs).count()

        context['filter_counts'] = counts
        return context


class ListActionMixin:
    """
    Mixin for ListView to provide model metadata for list actions.
    Automatically adds model_app_label, model_name, and model_class to context.
    Supports ?per_page= query parameter to override paginate_by at runtime.

    Usage in ListView:
        class MyModelListView(ListActionMixin, ListView):
            model = MyModel
            template_name = 'myapp/list.html'
    """

    # Optional: Override to customize the create button label
    create_button_label = None
    _ALLOWED_PAGE_SIZES = {10, 25, 50}

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get('per_page')
        if per_page and per_page.isdigit() and int(per_page) in self._ALLOWED_PAGE_SIZES:
            return int(per_page)
        return super().get_paginate_by(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_app_label'] = self.model._meta.app_label
        context['model_name'] = self.model._meta.model_name
        context['model_class'] = self.model
        context['current_per_page'] = self.get_paginate_by(self.get_queryset())

        # Add custom create button label if set
        if self.create_button_label:
            context['create_button_label'] = self.create_button_label

        return context


from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q

# 具備完整管理權限的 Groups（CPA、管理層、系統管理員）
_MANAGEMENT_GROUPS = ['CPA', 'management', 'Admin']
# 業務模組（記帳/行政/基本資料）可存取的 Groups
_BUSINESS_GROUPS  = _MANAGEMENT_GROUPS + ['A組', 'B組', 'C組']
# HR 模組可存取的 Groups
_HR_GROUPS        = _MANAGEMENT_GROUPS + ['人資組']


class GroupRequiredMixin:
    """
    Base mixin：限制只有特定 Groups 的使用者才能存取 view。
    Superuser 永遠通過。未登入者導向登入頁，已登入但無權限者回 403。

    通過條件（任一即可）：
    1. 在 allowed_groups 列表的 Group 中
    2. 透過任何 Group 擁有 allowed_app_labels 指定 app 的至少一個 Django permission
    """
    allowed_groups = []
    allowed_app_labels = []   # 子類別可設定，例如 ['hr']

    def _has_app_permission(self, user):
        """Check if user has any Django permission for the specified apps via their groups."""
        if not self.allowed_app_labels:
            return False
        return user.groups.filter(
            permissions__content_type__app_label__in=self.allowed_app_labels
        ).exists()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if request.user.groups.filter(name__in=self.allowed_groups).exists():
            return super().dispatch(request, *args, **kwargs)
        if self._has_app_permission(request.user):
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


class BusinessRequiredMixin(GroupRequiredMixin):
    """
    記帳/行政業務模組入口。
    允許：CPA、management、Admin、A組、B組、C組
    或：透過 Group permissions 擁有 bookkeeping/administrative/basic_data/registration/internal_accounting 的存取權
    """
    allowed_groups = _BUSINESS_GROUPS
    allowed_app_labels = ['bookkeeping', 'administrative', 'basic_data', 'registration', 'internal_accounting']


class HRRequiredMixin(GroupRequiredMixin):
    """
    HR 模組入口（薪資、出勤、請假為敏感資料）。
    允許：CPA、management、Admin、人資組
    或：透過 Group permissions 擁有 hr app 的存取權
    """
    allowed_groups = _HR_GROUPS
    allowed_app_labels = ['hr']


class ManagerRequiredMixin(UserPassesTestMixin):
    """
    需要管理層以上權限（CPA、management、Admin 或 superuser）。
    """
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.groups.filter(name__in=_MANAGEMENT_GROUPS).exists()


class EmployeeDataIsolationMixin:
    """
    依使用者角色過濾 queryset，確保一般員工只能看自己負責的資料。

    Rules:
    - Superuser 或管理層（_MANAGEMENT_GROUPS）：看全部
    - clientUser：看不到任何東西
    - 一般員工：依 employee_filter_fields 過濾自己負責的資料
    - 沒有 employee_profile：看不到任何東西

    Usage:
        class MyModelListView(EmployeeDataIsolationMixin, ListView):
            employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']
    """
    employee_filter_fields = []

    def get_employee_filter_fields(self):
        return self.employee_filter_fields

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # 1. Superuser 或管理層：看全部
        if user.is_superuser or user.groups.filter(name__in=_MANAGEMENT_GROUPS).exists():
            return qs

        # 2. 外部客戶帳號：看不到任何東西
        if user.groups.filter(name='clientUser').exists():
            return qs.none()
            
        # 3. Regular employee: filter by assigned fields
        if hasattr(user, 'employee_profile') and user.employee_profile:
            emp = user.employee_profile
            filter_fields = self.get_employee_filter_fields()
            
            if not filter_fields:
                return qs.none() # If no fields defined, safe default is none
                
            # Build OR condition for all specified fields
            q_objects = Q()
            for field in filter_fields:
                q_objects |= Q(**{field: emp})
                
            return qs.filter(q_objects)
            
        # 4. No employee profile: see nothing
        return qs.none()


# 能看到「所有人」HR 資料的群組（人資專責 + CPA + Admin）
_HR_FULL_ACCESS_GROUPS = ['CPA', 'Admin', '人資組']

# 出勤 / 請假可額外開放 management 群組看全部
_HR_ATTENDANCE_ACCESS_GROUPS = _HR_FULL_ACCESS_GROUPS + ['management']


class OwnEmployeeDataMixin:
    """
    Row-level isolation for personal HR data.

    存取規則：
    - Superuser 或 full_access_groups 成員：看全部
    - supervisor_bypass=True（預設）：其他人看自己 + 直屬部屬
    - supervisor_bypass=False：其他人只看自己
    - 無 employee_profile：什麼都看不到

    子類別可覆寫：
        full_access_groups    薪資 → _HR_FULL_ACCESS_GROUPS（不含 management）
                              出勤/請假 → _HR_ATTENDANCE_ACCESS_GROUPS（含 management）
        supervisor_bypass     薪資 → False（management 只看自己）
                              出勤/請假 → True（management 可看部屬）
    """
    employee_fk_field = 'employee'
    full_access_groups = _HR_FULL_ACCESS_GROUPS
    supervisor_bypass = True   # 薪資相關 view 請設為 False

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser or user.groups.filter(name__in=self.full_access_groups).exists():
            return qs

        emp = getattr(user, 'employee_profile', None)
        if not emp:
            return qs.none()

        if self.supervisor_bypass:
            # 自己的資料 + 直屬部屬的資料
            return qs.filter(
                Q(**{self.employee_fk_field: emp}) |
                Q(**{f'{self.employee_fk_field}__supervisor': user})
            )
        else:
            # 只看自己
            return qs.filter(**{self.employee_fk_field: emp})


class PayrollDataMixin(OwnEmployeeDataMixin):
    """
    薪資相關資料隔離：management 只看自己（無 supervisor bypass）。
    用於薪資單、加班、代墊款等敏感薪酬資料的 views。
    """
    supervisor_bypass = False
