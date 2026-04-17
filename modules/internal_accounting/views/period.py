from django.contrib import messages
from core.mixins import BusinessRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView
from django.views.decorators.http import require_POST

from ..models.period import AccountingPeriod
from ..services import AccountingService


class AccountingPeriodListView(BusinessRequiredMixin, ListView):
    model = AccountingPeriod
    template_name = 'period/list.html'
    context_object_name = 'periods'

    def get_queryset(self):
        return AccountingPeriod.objects.order_by('-year', 'month')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '會計期間管理'

        periods_by_year = {}
        for period in context['periods']:
            periods_by_year.setdefault(period.year, []).append(period)
        # sorted descending by year
        context['periods_by_year'] = dict(sorted(periods_by_year.items(), reverse=True))
        context['latest_year'] = max(periods_by_year.keys()) if periods_by_year else None
        return context

    def post(self, request, *args, **kwargs):
        year = request.POST.get('year', '').strip()
        if not year or not year.isdigit():
            messages.error(request, '請輸入有效的年度數字。')
            return redirect('internal_accounting:period_list')

        year = int(year)
        created = 0
        for month in range(1, 13):
            _, is_new = AccountingPeriod.objects.get_or_create(year=year, month=month)
            if is_new:
                created += 1

        if created:
            messages.success(request, f'已為 {year} 年建立 {created} 個會計期間。')
        else:
            messages.info(request, f'{year} 年的 12 個會計期間已全部存在。')

        return redirect('internal_accounting:period_list')


@login_required
@require_POST
def toggle_period_status(request, pk):
    period = get_object_or_404(AccountingPeriod, pk=pk)
    if period.status == AccountingPeriod.Status.OPEN:
        period.status = AccountingPeriod.Status.CLOSED
        messages.success(request, f'{period.year} 年 {period.month:02d} 月已關帳。')
    else:
        period.status = AccountingPeriod.Status.OPEN
        messages.success(request, f'{period.year} 年 {period.month:02d} 月已重新開帳。')
    period.save(update_fields=['status'])
    return redirect('internal_accounting:period_list')


@login_required
@require_POST
def close_year_action(request):
    year = request.POST.get('year', '').strip()
    if not year or not year.isdigit():
        messages.error(request, '請提供有效的年度。')
        return redirect('internal_accounting:period_list')

    try:
        year = int(year)
        voucher, msg = AccountingService.close_year(year, request.user)
        if voucher:
            messages.success(request, f'{msg}，傳票編號：{voucher.voucher_no}')
        else:
            messages.warning(request, msg)
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'年度結轉失敗：{e}')

    return redirect('internal_accounting:period_list')


@login_required
@require_POST
def run_depreciation_action(request):
    year = request.POST.get('year', '').strip()
    month = request.POST.get('month', '').strip()
    if not year or not month:
        messages.error(request, '請提供年度與月份。')
        return redirect('internal_accounting:period_list')

    try:
        year = int(year)
        month = int(month)
        voucher, msg = AccountingService.run_monthly_depreciation(year, month, request.user)
        if voucher:
            AccountingPeriod.objects.filter(year=year, month=month).update(depreciation_done=True)
            messages.success(request, f'{msg}（傳票：{voucher.voucher_no}）')
        else:
            messages.warning(request, msg)
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'折舊提列失敗：{e}')

    return redirect('internal_accounting:period_list')
