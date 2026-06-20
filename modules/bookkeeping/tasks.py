"""
Bookkeeping celery tasks。

主要把會跑久的批次工作（月結帳單）移出 request thread。
"""
import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from django.db import transaction


logger = logging.getLogger(__name__)


def _parse_date(s, default):
    if not s:
        return default
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default


@shared_task(name='bookkeeping.generate_bills_batch')
def generate_bills_batch(year: int, month: int,
                         bill_date_str: str = '', due_date_str: str = '',
                         annual_override: str = '') -> dict:
    """
    批次產生月帳單（背景跑，不卡 request thread）。

    Args:
        year: 帳單年度
        month: 帳單月份 (1-12)
        bill_date_str: 開立日期 'YYYY-MM-DD'，空字串用今天
        due_date_str: 應繳日期 'YYYY-MM-DD'，空字串用 +30 天
        annual_override: 'yes' 強制全部按年費、'no' 強制按月費、'' 依各客戶設定

    Returns:
        {'created': N, 'skipped': M, 'message': '...'}
    """
    from modules.bookkeeping.models import ClientBill
    from modules.bookkeeping.views.bill_views import _get_clients_for_batch, _build_quotation_data

    today = date.today()
    bill_date = _parse_date(bill_date_str, today)
    due_date = _parse_date(due_date_str, today + timedelta(days=30))

    candidates = _get_clients_for_batch(month)
    if annual_override == 'yes':
        for c in candidates:
            c['is_annual'] = True
    elif annual_override == 'no':
        for c in candidates:
            c['is_annual'] = False

    created_count = skipped_count = 0
    with transaction.atomic():
        for c in candidates:
            active_fee = c['active_fee']
            is_annual = c['is_annual']
            quotation_data = _build_quotation_data(active_fee, year, month, is_annual)
            total = sum(r['amount'] for r in quotation_data)

            _, created = ClientBill.objects.get_or_create(
                client=c['client'],
                year=year,
                month=month,
                defaults={
                    'bill_date': bill_date,
                    'due_date': due_date,
                    'status': ClientBill.BillStatus.DRAFT,
                    'quotation_data': quotation_data,
                    'cost_sharing_data': c['client'].cost_sharing_data or [],
                    'total_amount': total,
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

    msg = f'批次產帳完成：新建 {created_count} 筆，跳過 {skipped_count} 筆（已存在）'
    logger.info(msg)
    return {'created': created_count, 'skipped': skipped_count, 'message': msg}


@shared_task(name='bookkeeping.send_remuneration_reminders')
def send_remuneration_reminders() -> dict:
    """
    每月勞報繳費提醒（Celery Beat 每月 1 號觸發）。

    掃描上個月支付、扣繳或保費仍待繳納的勞報單，
    依客戶通知偏好（Email/LINE）匯總提醒。
    走 management command 同一條路，admin 的 ScheduledJob 狀態會一併更新；
    手動測試：docker-compose exec web python manage.py send_remuneration_reminders
    """
    from django.core.management import call_command

    call_command('send_remuneration_reminders')
    logger.info('勞報繳費提醒 task 執行完成')
    return {'ok': True}


@shared_task(name='bookkeeping.send_onboarding_sla_reminders')
def send_onboarding_sla_reminders() -> dict:
    """每日記帳交接 SLA 催促（Celery Beat 每日觸發）。

    掃描遲未指派 / 遲未首次聯繫的 onboarding 客戶，發 digest 給組長/助理/合夥人。
    走 management command 同一條路，admin 的 ScheduledJob 狀態會一併更新；
    手動測試：docker compose exec web python manage.py send_onboarding_sla_reminders --dry-run
    """
    from django.core.management import call_command

    call_command('send_onboarding_sla_reminders')
    logger.info('記帳交接 SLA 催促 task 執行完成')
    return {'ok': True}
