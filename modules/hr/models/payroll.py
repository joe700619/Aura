from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class InsuranceBracket(BaseModel):
    """
    勞健保投保級距表
    維護每年的級距與其對應的 7 項保費金額。
    """
    level_name = models.CharField(_('級別名稱'), max_length=50, help_text='例如：第 1 級')
    insured_salary = models.DecimalField(_('投保薪資'), max_digits=10, decimal_places=0)
    
    # 員工自付
    labor_employee = models.DecimalField(_('勞保-自付'), max_digits=10, decimal_places=0, default=0)
    health_employee = models.DecimalField(_('健保-自付'), max_digits=10, decimal_places=0, default=0)
    
    # 雇主負擔
    labor_employer = models.DecimalField(_('勞保-雇主'), max_digits=10, decimal_places=0, default=0)
    health_employer = models.DecimalField(_('健保-雇主'), max_digits=10, decimal_places=0, default=0)
    pension_employer = models.DecimalField(_('勞退-雇主'), max_digits=10, decimal_places=0, default=0)
    
    # 其他負擔
    occupational_hazard = models.DecimalField(_('職災費'), max_digits=10, decimal_places=0, default=0)
    wage_arrears = models.DecimalField(_('工資墊償'), max_digits=10, decimal_places=0, default=0)

    class Meta:
        ordering = ['insured_salary']
        verbose_name = _('勞健保投保級距')
        verbose_name_plural = _('勞健保投保級距')

    def __str__(self):
        return f"{self.level_name} - 投保薪資: {self.insured_salary}"



class SalaryStructure(BaseModel):
    """
    薪資結構
    定義每位員工的底薪、津貼、勞健保扣除額等。
    可有多筆紀錄（歷次調薪），以 is_current 標示目前生效的結構。
    """

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='salary_structures',
        verbose_name=_('員工'),
    )
    base_salary = models.DecimalField(_('底薪'), max_digits=10, decimal_places=0, default=0)
    meal_allowance = models.DecimalField(_('伙食津貼'), max_digits=10, decimal_places=0, default=0)
    transport_allowance = models.DecimalField(_('交通津貼'), max_digits=10, decimal_places=0, default=0)
    other_allowance = models.DecimalField(_('其他津貼'), max_digits=10, decimal_places=0, default=0)
    labor_insurance = models.DecimalField(_('勞保自付額'), max_digits=10, decimal_places=0, default=0)
    health_insurance = models.DecimalField(_('健保自付額'), max_digits=10, decimal_places=0, default=0)
    
    # 雇主負擔
    labor_insurance_employer = models.DecimalField(_('勞保費_雇主負擔'), max_digits=10, decimal_places=0, default=0)
    health_insurance_employer = models.DecimalField(_('健保費_雇主負擔'), max_digits=10, decimal_places=0, default=0)
    pension_employer = models.DecimalField(_('退休金_雇主負擔'), max_digits=10, decimal_places=0, default=0)
    occupational_hazard_employer = models.DecimalField(_('職災費'), max_digits=10, decimal_places=0, default=0)
    wage_arrears_employer = models.DecimalField(_('工資墊償金'), max_digits=10, decimal_places=0, default=0)

    effective_date = models.DateField(_('生效日期'))
    is_current = models.BooleanField(_('目前生效'), default=True)
    note = models.TextField(_('備註'), blank=True, default='')

    class Meta:
        ordering = ['-effective_date']
        verbose_name = _('薪資結構')
        verbose_name_plural = _('薪資結構')

    def __str__(self):
        return f"{self.employee.name} - 底薪 {self.base_salary} ({'生效中' if self.is_current else '已過期'})"

    @property
    def total_allowance(self):
        return self.meal_allowance + self.transport_allowance + self.other_allowance

    @property
    def total_deduction(self):
        return self.labor_insurance + self.health_insurance

    def save(self, *args, **kwargs):
        # 如果設為生效中，將同一員工其他結構設為非生效
        if self.is_current:
            SalaryStructure.objects.filter(
                employee=self.employee, is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class OvertimeRecord(BaseModel):
    """
    加班紀錄
    記錄員工某日的加班分鐘數；加班費依加班日期自動判定類別、
    並依勞基法級距加權計算（見 services/overtime_calculator.py）。
    """

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='overtime_records',
        verbose_name=_('員工'),
    )
    date = models.DateField(_('加班日期'))
    minutes = models.PositiveIntegerField(
        _('加班分鐘'),
        default=0,
        help_text=_('當日加班總分鐘數，系統會依日期自動分類並依級距加權計算加班費'),
    )
    reason = models.TextField(_('加班事由'), blank=True, default='')
    is_approved = models.BooleanField(_('是否已核准'), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_overtimes',
        verbose_name=_('核准人'),
    )

    class Meta:
        ordering = ['-date']
        verbose_name = _('加班紀錄')
        verbose_name_plural = _('加班紀錄')

    def __str__(self):
        return f"{self.employee.name} - {self.date} ({self.minutes}分 / {self.day_type_label})"

    @property
    def hours_display(self):
        """加班時數（小時，供顯示用）。"""
        from decimal import Decimal
        return (Decimal(self.minutes) / Decimal('60')).quantize(Decimal('0.1'))

    @property
    def day_type(self):
        """依加班日期自動判定的加班類別代碼。"""
        from ..services.overtime_calculator import classify_overtime_day
        return classify_overtime_day(self.date)

    @property
    def day_type_label(self):
        """加班類別中文（平日/休息日/國定假日/例假）。"""
        from ..services.overtime_calculator import DAY_TYPE_LABELS
        return DAY_TYPE_LABELS.get(self.day_type, self.day_type)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hr:overtime_update', kwargs={'pk': self.pk})

    # ========== Approval Workflow Helper Methods ==========

    def get_approval_request(self):
        """取得當前的核准請求"""
        from modules.workflow.services import get_approval_request
        return get_approval_request(self)

    def can_submit_for_approval(self):
        """是否可以送出核准"""
        approval = self.get_approval_request()
        if not approval:
            return True
        return approval.status in ['DRAFT', 'RETURNED']

    def can_user_approve(self, user):
        """檢查使用者是否可以核准此加班單"""
        from modules.workflow.services import get_effective_approver

        approval = self.get_approval_request()
        if not approval or approval.status != 'PENDING':
            return False

        if not approval.current_step:
            return False

        step_approver = approval.current_step.get_approver(self)
        if not step_approver:
            return False

        from django.contrib.auth.models import Group
        if isinstance(step_approver, Group):
            if user.groups.filter(id=step_approver.id).exists():
                return True
            effective_approver, _ = get_effective_approver(user, approval)
            return effective_approver != user
        else:
            effective_approver, original = get_effective_approver(step_approver, approval)
            return effective_approver == user

    def can_user_cancel(self, user):
        """檢查使用者是否可以撤回"""
        approval = self.get_approval_request()
        if not approval:
            return False
        return approval.requester == user and approval.status in ['PENDING', 'RETURNED']

    @property
    def overtime_pay(self):
        """
        計算加班費：時薪 × 加權分鐘 / 60。
        依加班日期自動判定類別（平日/休息日/國定假日/例假），
        再依勞基法級距把加班分鐘加權（跨級距自動拆算）。
        """
        from ..services.overtime_calculator import calculate_overtime_pay
        # 時薪需從 SalaryStructure 取得
        salary = SalaryStructure.objects.filter(
            employee=self.employee, is_current=True
        ).first()
        if not salary:
            return 0
        # 月薪制平日每小時工資額 = 底薪 / 30 / 8（法定 月薪/240，僅採底薪）
        hourly_rate = salary.base_salary / 30 / 8
        return calculate_overtime_pay(hourly_rate, self.day_type, self.minutes)


class PayrollRecord(BaseModel):
    """
    薪資單
    每月為每位員工計算的薪資明細。
    """

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_records',
        verbose_name=_('員工'),
    )
    year_month = models.CharField(_('年月'), max_length=7, help_text='格式: 2026-03')

    # 出勤
    work_days_required = models.IntegerField(_('應出勤天數'), default=0)
    work_days_actual = models.IntegerField(_('實際出勤天數'), default=0)

    # 薪資項目
    base_salary = models.DecimalField(_('底薪'), max_digits=10, decimal_places=0, default=0)
    meal_allowance = models.DecimalField(_('伙食津貼'), max_digits=10, decimal_places=0, default=0)
    transport_allowance = models.DecimalField(_('交通津貼'), max_digits=10, decimal_places=0, default=0)
    other_allowance = models.DecimalField(_('其他津貼'), max_digits=10, decimal_places=0, default=0)
    overtime_pay = models.DecimalField(_('加班費'), max_digits=10, decimal_places=0, default=0)
    bonus_pay = models.DecimalField(_('獎金/年終/績效'), max_digits=10, decimal_places=0, default=0)
    leave_settlement_pay = models.DecimalField(_('特休折算薪資'), max_digits=10, decimal_places=0, default=0)
    advance_payment_deduction = models.DecimalField(_('代墊款歸還'), max_digits=10, decimal_places=0, default=0)
    gross_salary = models.DecimalField(_('應發合計'), max_digits=10, decimal_places=0, default=0)

    # 扣除
    labor_insurance = models.DecimalField(_('勞保扣除'), max_digits=10, decimal_places=0, default=0)
    health_insurance = models.DecimalField(_('健保扣除'), max_digits=10, decimal_places=0, default=0)
    leave_deduction = models.DecimalField(_('請假扣款'), max_digits=10, decimal_places=0, default=0)
    late_deduction = models.DecimalField(_('遲到扣款'), max_digits=10, decimal_places=0, default=0)
    missing_punch_deduction = models.DecimalField(_('缺卡扣款'), max_digits=10, decimal_places=0, default=0)
    other_deduction = models.DecimalField(_('其他扣除'), max_digits=10, decimal_places=0, default=0)

    # 實發
    net_salary = models.DecimalField(_('實發金額'), max_digits=10, decimal_places=0, default=0)

    is_finalized = models.BooleanField(_('是否已確認'), default=False)
    note = models.TextField(_('備註'), blank=True, default='')

    class Meta:
        ordering = ['-year_month', 'employee__employee_number']
        verbose_name = _('薪資單')
        verbose_name_plural = _('薪資單')
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'year_month'],
                name='unique_employee_payroll_month',
            )
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.year_month} (實發 {self.net_salary})"

    def scan_attendance_days(self, year, month):
        """
        逐日掃描當月工作日，回傳每日出勤明細（遲到分鐘、缺卡次數、起算點等）。

        calculate()（算總額）與「明細」頁（顯示逐日）共用此方法，
        確保金額與明細出自同一套邏輯、不會兩邊各算各的對不起來。

        回傳 list[dict]，每筆為一個工作日。
        """
        import calendar
        from datetime import date as dt_date, time as dt_time, datetime
        from django.utils.timezone import make_aware, localtime
        from ..models import WorkCalendar, AttendanceRecord
        from ..models.leave import LeaveRequest

        _, days_in_month = calendar.monthrange(year, month)
        details = []

        for day in range(1, days_in_month + 1):
            d = dt_date(year, month, day)
            if not WorkCalendar.is_workday(d):
                continue

            day_start = make_aware(datetime.combine(d, dt_time.min))
            day_end = make_aware(datetime.combine(d, dt_time.max))
            leaves = LeaveRequest.objects.filter(
                employee=self.employee, status='approved',
                start_datetime__lt=day_end, end_datetime__gt=day_start,
                is_deleted=False,
            )

            is_full_day_leave = False
            has_any_leave = False
            morning_leave_end = None
            for leave in leaves:
                has_any_leave = True
                start_local = localtime(leave.start_datetime).time()
                end_local = localtime(leave.end_datetime).time()
                if start_local <= dt_time(8, 45) and end_local >= dt_time(17, 0):
                    is_full_day_leave = True
                if start_local <= dt_time(8, 45):
                    if morning_leave_end is None or end_local > morning_leave_end:
                        morning_leave_end = end_local

            row = {
                'date': d, 'weekday': d.weekday(),
                'clock_in': None, 'clock_out': None,
                'is_full_day_leave': is_full_day_leave,
                'has_any_leave': has_any_leave,
                'late_limit': None, 'late_minutes': 0,
                'missing_punches': 0, 'missing_reason': '',
                'counts_as_actual': False,
            }

            if is_full_day_leave:
                # 全天假不檢查打卡與遲到
                details.append(row)
                continue

            # 當天有任何核准請假 → 該日不計缺卡（部分時段假豁免）
            count_missing = not has_any_leave
            attendance = AttendanceRecord.objects.filter(
                employee=self.employee, date=d, is_deleted=False,
            ).first()

            if not attendance:
                if count_missing:
                    row['missing_punches'] = 2
                    row['missing_reason'] = '未出勤（視同曠職）'
            else:
                row['clock_in'] = attendance.clock_in
                row['clock_out'] = attendance.clock_out
                if attendance.clock_in and attendance.clock_out:
                    row['counts_as_actual'] = True
                elif attendance.clock_in or attendance.clock_out:
                    row['counts_as_actual'] = True
                    if count_missing:
                        row['missing_punches'] = 1
                        row['missing_reason'] = '漏打下班卡' if attendance.clock_in else '漏打上班卡'
                else:
                    if count_missing:
                        row['missing_punches'] = 2
                        row['missing_reason'] = '上下班卡皆無'

                # 遲到（起算點依當天請假涵蓋時間動態決定）
                if attendance.clock_in:
                    if morning_leave_end is None:
                        limit_time = dt_time(9, 0)
                    else:
                        limit_time = max(dt_time(9, 0), morning_leave_end)
                        if dt_time(12, 0) <= limit_time < dt_time(13, 0):
                            limit_time = dt_time(13, 0)
                    row['late_limit'] = limit_time
                    if attendance.clock_in > limit_time:
                        late_delta = datetime.combine(d, attendance.clock_in) - datetime.combine(d, limit_time)
                        row['late_minutes'] = int(late_delta.total_seconds() // 60)

            details.append(row)

        return details

    def get_detail(self):
        """
        即時重算產生薪資明細（遲到/缺卡/請假/加班），供薪資單「明細」頁顯示。

        與 calculate() 共用 scan_attendance_days，金額口徑一致（時薪=底薪/30/8）。
        注意：明細依「目前」的出勤/請假/加班資料即時產生；若薪資單結算後
        來源資料又有異動，明細的即時金額可能與已存的金額不同步（stale=True），
        畫面上會提示可按「重新計算」。
        """
        from decimal import Decimal, ROUND_HALF_UP
        from datetime import datetime
        from django.utils.timezone import make_aware
        from ..models import OvertimeRecord
        from ..models.leave import LeaveRequest

        year, month = int(self.year_month[:4]), int(self.year_month[5:7])
        salary = SalaryStructure.objects.filter(employee=self.employee, is_current=True).first()
        base = salary.base_salary if salary else Decimal('0')
        hourly_rate = base / Decimal('30') / Decimal('8')
        minute_rate = hourly_rate / Decimal('60')

        def yuan(x):
            return int(Decimal(x).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

        day_details = self.scan_attendance_days(year, month)
        late_rows = [r for r in day_details if r['late_minutes'] > 0]
        missing_rows = [r for r in day_details if r['missing_punches'] > 0]
        late_minutes = sum(r['late_minutes'] for r in late_rows)
        missing_count = sum(r['missing_punches'] for r in missing_rows)

        # 請假明細
        month_start = make_aware(datetime(year, month, 1))
        month_end = make_aware(datetime(year + (month // 12), (month % 12) + 1, 1))
        leaves = LeaveRequest.objects.filter(
            employee=self.employee, status='approved',
            start_datetime__gte=month_start, start_datetime__lt=month_end,
            is_deleted=False,
        ).select_related('leave_type').order_by('start_datetime')
        leave_rows = []
        unpaid_total = Decimal('0')
        for l in leaves:
            unpaid = (l.total_hours or Decimal('0')) * (Decimal('1') - l.leave_type.pay_rate)
            unpaid_total += unpaid
            leave_rows.append({'leave': l, 'unpaid_hours': unpaid})

        # 加班明細
        overtime_rows = list(OvertimeRecord.objects.filter(
            employee=self.employee, date__year=year, date__month=month,
            is_approved=True, is_deleted=False,
        ).order_by('date'))

        # 即時重算金額
        late_total = yuan(Decimal(late_minutes) * minute_rate)
        missing_total = yuan(Decimal(missing_count) * Decimal('4') * hourly_rate)
        leave_total = yuan(hourly_rate * unpaid_total)
        overtime_total = sum((o.overtime_pay for o in overtime_rows), 0)

        # 與已存金額比對，判斷是否已過時（結算後來源資料有變動）
        stale = (
            late_total != self.late_deduction
            or missing_total != self.missing_punch_deduction
            or leave_total != self.leave_deduction
            or overtime_total != self.overtime_pay
        )

        return {
            'hourly_rate': hourly_rate,
            'minute_rate': minute_rate,
            'late_rows': late_rows,
            'late_minutes': late_minutes,
            'late_total': late_total,
            'missing_rows': missing_rows,
            'missing_count': missing_count,
            'missing_total': missing_total,
            'leave_rows': leave_rows,
            'unpaid_total': unpaid_total,
            'leave_total': leave_total,
            'overtime_rows': overtime_rows,
            'overtime_total': overtime_total,
            'stale': stale,
            'stored': {
                'late': self.late_deduction,
                'missing': self.missing_punch_deduction,
                'leave': self.leave_deduction,
                'overtime': self.overtime_pay,
            },
        }

    def calculate(self):
        """
        依據薪資結構、出勤、請假、加班計算薪資
        日薪 = 底薪 / 應出勤天數
        遲到 = 09:00 起算 (若請上午假則 13:00 起算)，每分鐘扣 (時薪/60)
        缺卡 = 缺一次打卡扣 4 小時薪資
        """
        from decimal import Decimal
        from django.utils.timezone import make_aware, localtime
        from datetime import datetime, date as dt_date, time as dt_time
        import calendar
        from ..models import WorkCalendar, AttendanceRecord, OvertimeRecord, AdvancePayment
        from ..models.leave import LeaveRequest, LeaveSettlementRecord

        year, month = int(self.year_month[:4]), int(self.year_month[5:7])

        # 1. 取得薪資結構
        salary = SalaryStructure.objects.filter(
            employee=self.employee, is_current=True
        ).first()
        if not salary:
            return

        self.base_salary = salary.base_salary
        self.meal_allowance = salary.meal_allowance
        self.transport_allowance = salary.transport_allowance
        self.other_allowance = salary.other_allowance
        self.labor_insurance = salary.labor_insurance
        self.health_insurance = salary.health_insurance

        # 2. 計算應出勤天數與薪資費率
        # work_days_required 仍計算並保存（顯示用：當月應出勤天數）。
        self.work_days_required = WorkCalendar.get_workdays_in_month(year, month)

        # 時薪/分薪基準統一為「月薪 / 30 / 8」(= 月薪/240，法定平日每小時工資額)，
        # 與加班費同一口徑（見 overtime_calculator）。
        # 不再用「當月應出勤天數」換算，避免同一人「請假/遲到/缺卡扣款時薪」
        # 與「加班時薪」基準不一致。請假扣款、遲到、缺卡均依此基準。
        hourly_rate = self.base_salary / Decimal('30') / Decimal('8')
        minute_rate = hourly_rate / Decimal('60')

        # 3. 逐日計算出勤、遲到與缺卡
        # 逐日掃描邏輯抽到 scan_attendance_days()，與「明細」頁共用同一套規則。
        day_details = self.scan_attendance_days(year, month)
        actual_days = sum(1 for r in day_details if r['counts_as_actual'])
        total_late_minutes = sum(r['late_minutes'] for r in day_details)
        total_missing_punches = sum(r['missing_punches'] for r in day_details)

        self.work_days_actual = actual_days

        # 4. 請假扣薪（無薪假總時數計算）
        month_start = make_aware(datetime(year, month, 1))
        if month == 12:
            month_end = make_aware(datetime(year + 1, 1, 1))
        else:
            month_end = make_aware(datetime(year, month + 1, 1))

        # 依「給薪比例」加權：全薪(1.0)扣0、半薪(0.5)扣半、無薪(0.0)全扣
        unpaid_hours = LeaveRequest.objects.filter(
            employee=self.employee,
            status='approved',
            start_datetime__gte=month_start,
            start_datetime__lt=month_end,
            is_deleted=False,
        ).aggregate(
            total=models.Sum(
                models.ExpressionWrapper(
                    models.F('total_hours') * (1 - models.F('leave_type__pay_rate')),
                    output_field=models.DecimalField(max_digits=10, decimal_places=2),
                )
            )
        )['total'] or Decimal('0')

        self.leave_deduction = round(hourly_rate * unpaid_hours)
        
        # 計算遲到與缺卡扣款額
        self.late_deduction = round(Decimal(total_late_minutes) * minute_rate)
        # 缺一次卡 = 扣 4 小時
        self.missing_punch_deduction = round(Decimal(total_missing_punches) * Decimal('4') * hourly_rate)

        # 5. 加班費
        overtime_records = OvertimeRecord.objects.filter(
            employee=self.employee,
            date__year=year,
            date__month=month,
            is_approved=True,
            is_deleted=False,
        )
        total_overtime = Decimal('0')
        for ot in overtime_records:
            total_overtime += ot.overtime_pay
        self.overtime_pay = total_overtime

        # 5b. 代墊款扣除 – 撈取「已核准待發放」的申請
        approved_advances = AdvancePayment.objects.filter(
            employee=self.employee,
            status='approved',
            is_deleted=False,
        )
        self.advance_payment_deduction = sum(
            ap.amount for ap in approved_advances
        ) or Decimal('0')

        # 5c. 特休折算薪資 – 撈取尚未綁定薪資單的結算紀錄
        unsettled_leaves = LeaveSettlementRecord.objects.filter(
            employee=self.employee,
            payroll_record__isnull=True,
        )
        self.leave_settlement_pay = sum(
            s.total_amount for s in unsettled_leaves
        ) or Decimal('0')

        # 6. 計算合計
        self.gross_salary = (
            self.base_salary
            + self.meal_allowance
            + self.transport_allowance
            + self.other_allowance
            + self.overtime_pay
            + self.bonus_pay
            + self.leave_settlement_pay  # 特休折算薪資是加項
            + self.advance_payment_deduction  # 代墊款歸還是加項
        )

        self.net_salary = (
            self.gross_salary
            - self.labor_insurance
            - self.health_insurance
            - self.leave_deduction
            - self.late_deduction
            - self.missing_punch_deduction
            - self.other_deduction
        )


class AdvancePayment(BaseModel):
    """
    代墊款申請
    記錄員工代墊公司的款項，核准後將在次月薪資自動併入應發合計一併發放。
    """
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('approved', '已核准 (待發放)'),
        ('deducted', '已發放 (依附薪資單)'),
        ('rejected', '已駁回'),
    ]

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='advance_payments',
        verbose_name=_('申請人'),
    )
    date_applied = models.DateField(_('申請日期'))
    amount = models.DecimalField(_('代墊金額'), max_digits=10, decimal_places=0)
    reason = models.TextField(_('代墊事由'))
    
    # 簽核與發放狀態
    status = models.CharField(_('狀態'), max_length=20, choices=STATUS_CHOICES, default='pending')
    is_approved = models.BooleanField(_('是否已核准'), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_advance_payments',
        verbose_name=_('核准人'),
    )

    # 關聯的薪資單紀錄
    payroll_record = models.ForeignKey(
        'hr.PayrollRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_advance_payments',
        verbose_name=_('發放於哪期薪資單'),
        help_text=_('綁定薪資單，當薪資單確認時自動轉為已發放。')
    )

    class Meta:
        ordering = ['-date_applied', '-created_at']
        verbose_name = _('代墊款申請')
        verbose_name_plural = _('代墊款申請')

    def __str__(self):
        return f"{self.employee.name} - {self.date_applied} ({self.amount})"

    def get_absolute_url(self):
        return reverse('hr:advance_payment_update', kwargs={'pk': self.pk})

    def get_approval_request(self):
        """取得關聯的簽核單"""
        from modules.workflow.models import ApprovalRequest
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(self)
        return ApprovalRequest.objects.filter(content_type=ct, object_id=self.pk).first()

    def can_submit_for_approval(self):
        """是否可以送出核准"""
        approval = self.get_approval_request()
        if not approval:
            return True
        return approval.status in ['DRAFT', 'RETURNED']

    def can_user_approve(self, user):
        """檢查使用者是否可以核准此代墊款"""
        from modules.workflow.services import get_effective_approver

        approval = self.get_approval_request()
        if not approval or approval.status != 'PENDING':
            return False

        if not approval.current_step:
            return False

        step_approver = approval.current_step.get_approver(self)
        if not step_approver:
            return False

        from django.contrib.auth.models import Group
        if isinstance(step_approver, Group):
            if user.groups.filter(id=step_approver.id).exists():
                return True
            effective_approver, _ = get_effective_approver(user, approval)
            return effective_approver != user
        else:
            effective_approver, original = get_effective_approver(step_approver, approval)
            return effective_approver == user

    def can_user_cancel(self, user):
        """檢查使用者是否可以撤回"""
        approval = self.get_approval_request()
        if not approval:
            return False
        return approval.requester == user and approval.status in ['PENDING', 'RETURNED']
