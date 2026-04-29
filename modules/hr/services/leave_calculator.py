"""
勞基法特休/病假計算邏輯（週年制）

特休假（Annual Leave）依勞基法第 38 條，從到職日起算：
- 6 個月以上 1 年未滿：3 天
- 1 年以上 2 年未滿：7 天
- 2 年以上 3 年未滿：10 天
- 3 年以上 5 年未滿：14 天
- 5 年以上 10 年未滿：15 天
- 10 年以上，每多 1 年加 1 天，最多 30 天

病假（Sick Leave）：
- 曆年制，每年 1/1~12/31 固定 30 天

其他假別（喪假等）由人工手動給假，不在自動計算範圍內。
"""

import logging
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from ..models import Employee, LeaveType, LeaveBalance

logger = logging.getLogger(__name__)

# 每天以 8 小時計
HOURS_PER_DAY = 8

# 勞基法特休對照表：(最小月數, 天數, 階段描述)
ANNUAL_LEAVE_TABLE = [
    (6,   3,  '6個月~1年'),
    (12,  7,  '1年~2年'),
    (24,  10, '2年~3年'),
    (36,  14, '3年~5年'),
    (60,  15, '5年~10年'),
    # 10 年以上由程式計算
]


def get_annual_leave_days(hire_date: date, reference_date: date) -> int:
    """
    依勞基法計算在 reference_date 時應有的特休天數。

    Args:
        hire_date: 到職日
        reference_date: 基準日

    Returns:
        特休天數
    """
    delta = relativedelta(reference_date, hire_date)
    total_months = delta.years * 12 + delta.months
    years = delta.years

    if total_months < 6:
        return 0
    elif years < 1:
        return 3
    elif years < 2:
        return 7
    elif years < 3:
        return 10
    elif years < 5:
        return 14
    elif years < 10:
        return 15
    else:
        # 10 年以上，每多 1 年加 1 天，上限 30 天
        return min(15 + (years - 9), 30)


def get_current_entitlement(hire_date: date, today: date = None):
    """
    計算員工目前所處的特休階段和有效期間。

    Args:
        hire_date: 到職日
        today: 今天（預設 date.today()）

    Returns:
        dict: {
            'days': int,
            'hours': Decimal,
            'period_start': date,
            'period_end': date,
            'seniority_desc': str,
        } or None (年資不足 6 個月)
    """
    if today is None:
        today = date.today()

    delta = relativedelta(today, hire_date)
    total_months = delta.years * 12 + delta.months
    years = delta.years

    if total_months < 6:
        return None

    # 判斷目前處於哪個年資階段
    if total_months < 12:
        # 6 個月 ~ 1 年：期間為 hire+6m ~ hire+1y
        days = 3
        period_start = hire_date + relativedelta(months=6)
        period_end = hire_date + relativedelta(years=1)
        desc = '滿6個月'
    else:
        # 1 年以上：期間為 hire+Ny ~ hire+(N+1)y
        days = get_annual_leave_days(hire_date, today)
        period_start = hire_date + relativedelta(years=years)
        period_end = hire_date + relativedelta(years=years + 1)
        desc = f'滿{years}年'

    return {
        'days': days,
        'hours': Decimal(str(days * HOURS_PER_DAY)),
        'period_start': period_start,
        'period_end': period_end,
        'seniority_desc': desc,
    }


def get_sick_leave_days() -> int:
    """病假每年固定 30 天"""
    return 30


def _ensure_leave_types():
    """確保所有標準假別的 LeaveType 存在（台灣勞基法 + 性別工作平等法）"""

    # ── 自動計算假別（sort_order 1~3）────────────────────────────────────
    annual_type, _ = LeaveType.objects.get_or_create(
        code='annual',
        defaults={
            'name': '特休',
            'is_paid': True,
            'max_hours_per_year': None,
            'requires_doc': False,
            'description': '依勞基法第38條（週年制）',
            'sort_order': 1,
        },
    )
    deferred_annual_type, _ = LeaveType.objects.get_or_create(
        code='deferred_annual',
        defaults={
            'name': '遞延特休',
            'is_paid': True,
            'max_hours_per_year': None,
            'requires_doc': False,
            'description': '上年度未休畢之特休遞延（期效一年）',
            'sort_order': 2,
        },
    )
    sick_type, _ = LeaveType.objects.get_or_create(
        code='sick',
        defaults={
            'name': '病假',
            'is_paid': True,
            'max_hours_per_year': Decimal(str(get_sick_leave_days() * HOURS_PER_DAY)),
            'requires_doc': True,
            'description': '每年30天（曆年制），需附醫療證明（超過3天）',
            'sort_order': 3,
        },
    )

    # ── 手動給假假別（sort_order 10 起）─────────────────────────────────
    # 事假：勞基法第43條，每年14天，無薪
    LeaveType.objects.get_or_create(
        code='personal',
        defaults={
            'name': '事假',
            'is_paid': False,
            'max_hours_per_year': Decimal('112'),  # 14天 × 8h
            'requires_doc': False,
            'description': '勞基法第43條，每年14天，無薪',
            'sort_order': 10,
        },
    )
    # 婚假：勞工請假規則第2條，8天，有薪
    LeaveType.objects.get_or_create(
        code='marriage',
        defaults={
            'name': '婚假',
            'is_paid': True,
            'max_hours_per_year': Decimal('64'),  # 8天 × 8h
            'requires_doc': True,
            'description': '勞工請假規則第2條，8天，有薪',
            'sort_order': 11,
        },
    )
    # 喪假：勞工請假規則第3條，天數依親屬關係（人工給假時依實際情形設定）
    LeaveType.objects.get_or_create(
        code='bereavement',
        defaults={
            'name': '喪假',
            'is_paid': True,
            'max_hours_per_year': None,
            'requires_doc': True,
            'description': '勞工請假規則第3條：父母/配偶/子女8天；祖父母/配偶父母/兄弟姊妹3~6天',
            'sort_order': 12,
        },
    )
    # 公傷病假：勞基法第59條，有薪，期限依傷情不限
    LeaveType.objects.get_or_create(
        code='work_injury',
        defaults={
            'name': '公傷病假',
            'is_paid': True,
            'max_hours_per_year': None,
            'requires_doc': True,
            'description': '勞基法第59條，因公受傷或患職業病，有薪',
            'sort_order': 13,
        },
    )
    # 生理假：勞工請假規則第4條，每月1天/全年3天，半薪
    LeaveType.objects.get_or_create(
        code='menstrual',
        defaults={
            'name': '生理假',
            'is_paid': True,  # 半薪（薪資計算時另行處理）
            'max_hours_per_year': Decimal('24'),  # 3天 × 8h
            'requires_doc': False,
            'description': '勞工請假規則第4條，每月1天每年3天，半薪（超出3天併計病假）',
            'sort_order': 14,
        },
    )
    # 產假：勞基法第50條，8週（分娩）或6週（流產）
    LeaveType.objects.get_or_create(
        code='maternity',
        defaults={
            'name': '產假',
            'is_paid': True,
            'max_hours_per_year': None,
            'requires_doc': True,
            'description': '勞基法第50條，分娩前後8週有薪，滿6個月以下工作者4週',
            'sort_order': 15,
        },
    )
    # 陪產假/陪產檢假：性別工作平等法第15條，7天，有薪
    LeaveType.objects.get_or_create(
        code='paternity',
        defaults={
            'name': '陪產假',
            'is_paid': True,
            'max_hours_per_year': Decimal('56'),  # 7天 × 8h
            'requires_doc': True,
            'description': '性別工作平等法第15條，7天有薪（含陪產檢假）',
            'sort_order': 16,
        },
    )
    # 育嬰留職停薪：性別工作平等法第16條，最長2年，無薪
    LeaveType.objects.get_or_create(
        code='parental',
        defaults={
            'name': '育嬰留停',
            'is_paid': False,
            'max_hours_per_year': None,
            'requires_doc': True,
            'description': '性別工作平等法第16條，最長2年，無薪',
            'sort_order': 17,
        },
    )
    # 家庭照顧假：性別工作平等法第20條，每年7天，併計事假
    LeaveType.objects.get_or_create(
        code='family_care',
        defaults={
            'name': '家庭照顧假',
            'is_paid': False,
            'max_hours_per_year': Decimal('56'),  # 7天 × 8h
            'requires_doc': False,
            'description': '性別工作平等法第20條，每年7天無薪，併計入事假天數',
            'sort_order': 18,
        },
    )
    # 公假：勞工請假規則第7條，依法令或業務需要，有薪
    LeaveType.objects.get_or_create(
        code='official',
        defaults={
            'name': '公假',
            'is_paid': True,
            'max_hours_per_year': None,
            'requires_doc': False,
            'description': '勞工請假規則第7條，依法令或公務需要，有薪',
            'sort_order': 19,
        },
    )

    personal_type, _ = LeaveType.objects.get_or_create(
        code='personal',
        defaults={
            'name': '事假',
            'is_paid': False,
            'max_hours_per_year': Decimal('112'),
            'requires_doc': False,
            'description': '勞基法第43條，每年14天，無薪',
            'sort_order': 10,
        },
    )
    menstrual_type, _ = LeaveType.objects.get_or_create(
        code='menstrual',
        defaults={
            'name': '生理假',
            'is_paid': True,
            'max_hours_per_year': Decimal('24'),
            'requires_doc': False,
            'description': '勞工請假規則第4條，每月1天每年3天，半薪（超出3天併計病假）',
            'sort_order': 14,
        },
    )
    return annual_type, deferred_annual_type, sick_type, personal_type, menstrual_type


def grant_leave_for_employee(employee, today: date = None):
    """
    為單一員工計算並建立/更新當前的特休和病假餘額，
    同時處理特休結轉與折算薪資。

    此函式在以下時機呼叫：
    - Employee 建立/更新時（via signal）
    - 管理員按下「重算」按鈕時

    Args:
        employee: Employee instance
        today: 基準日（預設 date.today()）

    Returns:
        list of result dicts
    """
    if today is None:
        today = date.today()

    if not employee.hire_date:
        return []

    results = []
    annual_type, deferred_annual_type, sick_type, personal_type, menstrual_type = _ensure_leave_types()

    # ==========================================
    # 1. 處理已到期的「遞延特休」-> 折算薪資
    # ==========================================
    expired_deferred_leaves = LeaveBalance.objects.filter(
        employee=employee,
        leave_type=deferred_annual_type,
        period_end__lte=today,
        is_settled=False,
    )
    
    # 取得員工目前時薪做為折算基準
    from ..models.payroll import SalaryStructure, LeaveSettlementRecord
    salary = SalaryStructure.objects.filter(employee=employee, is_current=True).first()
    hourly_rate = Decimal('0')
    if salary and salary.base_salary:
        hourly_rate = salary.base_salary / Decimal('30') / Decimal('8')
        
    for deferred_balance in expired_deferred_leaves:
        remaining = deferred_balance.remaining_hours
        if remaining > 0 and hourly_rate > 0:
            total_amount = round(remaining * hourly_rate)
            LeaveSettlementRecord.objects.create(
                employee=employee,
                leave_balance=deferred_balance,
                hours=remaining,
                hourly_rate=round(hourly_rate),
                total_amount=total_amount,
            )
            results.append({
                'employee': employee.name,
                'leave_type': '遞延特休',
                'days': float(remaining) / HOURS_PER_DAY,
                'hours': remaining,
                'period': f"折算金額: ${total_amount}",
                'seniority': '折算薪資',
                'action': 'settled',
            })
        
        # 不論有無剩餘時數，皆標記為已處理
        deferred_balance.is_settled = True
        deferred_balance.save(update_fields=['is_settled'])

    # ==========================================
    # 2. 處理已到期的「特休」-> 結轉為遞延特休
    # ==========================================
    expired_annual_leaves = LeaveBalance.objects.filter(
        employee=employee,
        leave_type=annual_type,
        period_end__lte=today,
        is_carried_over=False,
    )
    
    for annual_balance in expired_annual_leaves:
        remaining = annual_balance.remaining_hours
        if remaining > 0:
            # 建立遞延特休，期效為原本的 period_end 往後推一年
            deferred_period_start = annual_balance.period_end
            deferred_period_end = deferred_period_start + relativedelta(years=1)
            
            LeaveBalance.objects.create(
                employee=employee,
                leave_type=deferred_annual_type,
                year=deferred_period_start.year,
                period_start=deferred_period_start,
                period_end=deferred_period_end,
                entitled_hours=remaining,
                used_hours=Decimal('0'),
                manually_granted=False,
            )
            results.append({
                'employee': employee.name,
                'leave_type': '特休結轉',
                'days': float(remaining) / HOURS_PER_DAY,
                'hours': remaining,
                'period': f"{deferred_period_start} ~ {deferred_period_end}",
                'seniority': '轉入遞延',
                'action': 'carried_over',
            })
            
        # 標記為已結轉
        annual_balance.is_carried_over = True
        annual_balance.save(update_fields=['is_carried_over'])

    # ==========================================
    # 3. 處理當期「特休」（週年制）
    # ==========================================
    entitlement = get_current_entitlement(employee.hire_date, today)
    if entitlement:
        balance, created = LeaveBalance.objects.get_or_create(
            employee=employee,
            leave_type=annual_type,
            year=entitlement['period_start'].year,
            period_start=entitlement['period_start'],
            defaults={
                'period_end': entitlement['period_end'],
                'entitled_hours': entitlement['hours'],
                'used_hours': Decimal('0'),
                'manually_granted': False,
            },
        )

        if not created and not balance.manually_granted:
            updated = False
            if balance.entitled_hours != entitlement['hours']:
                balance.entitled_hours = entitlement['hours']
                updated = True
            if balance.period_end != entitlement['period_end']:
                balance.period_end = entitlement['period_end']
                updated = True
            if updated:
                balance.save(update_fields=['entitled_hours', 'period_end'])

        results.append({
            'employee': employee.name,
            'leave_type': '特休',
            'days': entitlement['days'],
            'hours': entitlement['hours'],
            'period': f"{entitlement['period_start']} ~ {entitlement['period_end']}",
            'seniority': entitlement['seniority_desc'],
            'action': 'created' if created else 'checked',
        })

    # ==========================================
    # 4. 處理病假（曆年制）
    # ==========================================
    current_year = today.year
    sick_hours = Decimal(str(get_sick_leave_days() * HOURS_PER_DAY))
    period_start = date(current_year, 1, 1)
    period_end = date(current_year, 12, 31)

    sick_balance, sick_created = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=sick_type,
        year=current_year,
        period_start=period_start,
        defaults={
            'period_end': period_end,
            'entitled_hours': sick_hours,
            'used_hours': Decimal('0'),
            'manually_granted': False,
        },
    )

    results.append({
        'employee': employee.name,
        'leave_type': '病假',
        'days': get_sick_leave_days(),
        'hours': sick_hours,
        'period': f"{period_start} ~ {period_end}",
        'seniority': f'{current_year}年度',
        'action': 'created' if sick_created else 'exists',
    })

    # ==========================================
    # 5. 事假（曆年制，每年14天）
    # ==========================================
    personal_hours = Decimal('112')  # 14天 × 8h
    personal_balance, personal_created = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=personal_type,
        year=current_year,
        period_start=period_start,
        defaults={
            'period_end': period_end,
            'entitled_hours': personal_hours,
            'used_hours': Decimal('0'),
            'manually_granted': False,
        },
    )
    results.append({
        'employee': employee.name,
        'leave_type': '事假',
        'days': 14,
        'hours': personal_hours,
        'period': f"{period_start} ~ {period_end}",
        'seniority': f'{current_year}年度',
        'action': 'created' if personal_created else 'exists',
    })

    # ==========================================
    # 6. 生理假（曆年制，每年3天，僅女性員工）
    # ==========================================
    if employee.gender == 'F':
        menstrual_hours = Decimal('24')  # 3天 × 8h
        menstrual_balance, menstrual_created = LeaveBalance.objects.get_or_create(
            employee=employee,
            leave_type=menstrual_type,
            year=current_year,
            period_start=period_start,
            defaults={
                'period_end': period_end,
                'entitled_hours': menstrual_hours,
                'used_hours': Decimal('0'),
                'manually_granted': False,
            },
        )
        results.append({
            'employee': employee.name,
            'leave_type': '生理假',
            'days': 3,
            'hours': menstrual_hours,
            'period': f"{period_start} ~ {period_end}",
            'seniority': f'{current_year}年度',
            'action': 'created' if menstrual_created else 'exists',
        })

    return results


def recalculate_leave_balances(dry_run: bool = False, today: date = None) -> list:
    """
    為所有在職員工重新計算假期餘額（週年制）。

    Args:
        dry_run: 若 True 則只計算不寫入
        today: 基準日

    Returns:
        list of dicts describing changes
    """
    if today is None:
        today = date.today()

    results = []
    employees = Employee.objects.filter(employment_status='ACTIVE', is_active=True)

    if dry_run:
        # Dry run: 只計算不寫入
        annual_type, deferred_annual_type, sick_type, personal_type, menstrual_type = _ensure_leave_types()
        for emp in employees:
            if not emp.hire_date:
                continue
            entitlement = get_current_entitlement(emp.hire_date, today)
            if entitlement:
                results.append({
                    'employee': emp.name,
                    'leave_type': '特休',
                    'days': entitlement['days'],
                    'hours': entitlement['hours'],
                    'period': f"{entitlement['period_start']} ~ {entitlement['period_end']}",
                    'seniority': entitlement['seniority_desc'],
                    'action': 'preview',
                })
            sick_hours = Decimal(str(get_sick_leave_days() * HOURS_PER_DAY))
            results.append({
                'employee': emp.name,
                'leave_type': '病假',
                'days': get_sick_leave_days(),
                'hours': sick_hours,
                'period': f"{today.year}-01-01 ~ {today.year}-12-31",
                'seniority': f'{today.year}年度',
                'action': 'preview',
            })
            results.append({
                'employee': emp.name,
                'leave_type': '事假',
                'days': 14,
                'hours': Decimal('112'),
                'period': f"{today.year}-01-01 ~ {today.year}-12-31",
                'seniority': f'{today.year}年度',
                'action': 'preview',
            })
            if emp.gender == 'F':
                results.append({
                    'employee': emp.name,
                    'leave_type': '生理假',
                    'days': 3,
                    'hours': Decimal('24'),
                    'period': f"{today.year}-01-01 ~ {today.year}-12-31",
                    'seniority': f'{today.year}年度（女性員工）',
                    'action': 'preview',
                })
    else:
        for emp in employees:
            emp_results = grant_leave_for_employee(emp, today)
            results.extend(emp_results)

    return results
