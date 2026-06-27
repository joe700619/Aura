"""
薪資發放後的單據鎖定。

規則（與使用者確認的「整月全凍」方案）：
- 當「涵蓋某單據的那個月薪資單已確認（is_finalized=True）」時，該月相關單據
  （加班、請假、出勤）一律鎖定：不可編輯、刪除、核准/撤回，也不可新增。
- 代墊款不綁月份，以 status=='deducted'（已隨某張已發放薪資單還款）為鎖定。
- 取消發放（is_finalized 改回 False）→ 自動解鎖（本判斷為即時推導，無需額外處理）。

Django admin 不套用此鎖定，保留 superuser 更正的逃生門。
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.timezone import localtime, is_aware

LOCK_MESSAGE = (
    '此單據所屬月份薪資已發放，已鎖定，不可修改／刪除／核准。'
    '如需更正，請先至該月薪資單取消「是否已確認」。'
)
LOCK_CREATE_MESSAGE = '該月份薪資已發放，無法新增此單據。如需補登，請先取消該月薪資單的「是否已確認」。'


def is_month_locked(employee, year, month) -> bool:
    """該員工該年月是否已有「已確認」的薪資單。"""
    from ..models.payroll import PayrollRecord
    ym = f'{year:04d}-{month:02d}'
    return PayrollRecord.objects.filter(
        employee=employee, year_month=ym, is_finalized=True, is_deleted=False,
    ).exists()


def is_locked_by_payroll(record) -> bool:
    """單一單據是否因薪資已發放而鎖定。"""
    from ..models.payroll import OvertimeRecord, AdvancePayment
    from ..models.attendance import AttendanceRecord
    from ..models.leave import LeaveRequest

    # 代墊款：已隨某張已發放薪資單還款
    if isinstance(record, AdvancePayment):
        return record.status == 'deducted'

    employee = getattr(record, 'employee', None)
    if employee is None:
        return False

    # 請假：依請假起始時間所屬月份（轉本地時間，與計算口徑一致）
    if isinstance(record, LeaveRequest):
        dt = record.start_datetime
        if not dt:
            return False
        local = localtime(dt) if is_aware(dt) else dt
        return is_month_locked(employee, local.year, local.month)

    # 加班 / 出勤：依其 date 欄位所屬月份
    if isinstance(record, (OvertimeRecord, AttendanceRecord)):
        d = record.date
        if not d:
            return False
        return is_month_locked(employee, d.year, d.month)

    return False


# ─────────────────────────────────────────────────────────────
# View 層套用工具
# ─────────────────────────────────────────────────────────────

class PayrollLockUpdateDeleteMixin:
    """
    套到 加班／請假／出勤／代墊款 的 Update / Delete view。
    所屬月份薪資已發放時：GET 變唯讀（沿用 can_save 機制），POST（存檔/刪除）擋下。
    """

    def _payroll_is_locked(self):
        obj = getattr(self, 'object', None)
        if obj is None:
            try:
                self.object = obj = self.get_object()
            except Exception:
                return False
        return is_locked_by_payroll(obj)

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST' and self._payroll_is_locked():
            messages.error(request, LOCK_MESSAGE)
            return redirect(request.path)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self._payroll_is_locked():
            context['can_save'] = False          # 沿用母版的 fieldset disabled / 隱藏儲存鈕
            context['payroll_locked'] = True
            context['payroll_locked_message'] = LOCK_MESSAGE
        return context


class PayrollLockCreateMixin:
    """
    套到 加班／請假／出勤 的 Create view：
    若新增單據的日期落在「已發放」的月份，禁止新增。
    `lock_date_field` 指向表單中存日期的欄位（請假為 start_datetime）。

    以覆寫 post() 實作（而非 form_valid），因為各 Create view 多半自訂了
    form_valid，會蓋掉 mixin 的 form_valid；而 post() 各 view 未覆寫。
    """
    lock_date_field = 'date'

    def _create_month_locked(self, form):
        employee = form.cleaned_data.get('employee')
        value = form.cleaned_data.get(self.lock_date_field)
        if not employee or not value:
            return False
        if hasattr(value, 'hour'):  # datetime → 取本地日期
            local = localtime(value) if is_aware(value) else value
            year, month = local.year, local.month
        else:                       # date
            year, month = value.year, value.month
        return is_month_locked(employee, year, month)

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        if form.is_valid():
            if self._create_month_locked(form):
                # 掛在日期欄位（母版錯誤區只列欄位錯誤，non-field 不會顯示）
                form.add_error(self.lock_date_field, LOCK_CREATE_MESSAGE)
                messages.error(request, LOCK_CREATE_MESSAGE)
                return self.form_invalid(form)
            return self.form_valid(form)
        return self.form_invalid(form)


def block_if_locked(model, redirect_url_name):
    """
    核准流程 function view 用：POST 時若該單據已鎖定，擋下並導回。
    用法：@block_if_locked(OvertimeRecord, 'hr:overtime_update')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, pk, *args, **kwargs):
            if request.method == 'POST':
                obj = model.objects.filter(pk=pk).first()
                if obj is not None and is_locked_by_payroll(obj):
                    messages.error(request, LOCK_MESSAGE)
                    return redirect(redirect_url_name, pk=pk)
            return view_func(request, pk, *args, **kwargs)
        return wrapper
    return decorator
