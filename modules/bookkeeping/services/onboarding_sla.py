"""記帳客戶 onboarding 斷點的 SLA 掃描與催促。

背景見《商工登記_端到端流程架構》§11.5。工商登記完成 → 客戶簽記帳委任書 →
自動建 BookkeepingClient（未指派）。之後兩段時鐘怕「沒人動」：

  時鐘 A 遲未指派：建檔(created_at)後 N 天仍無 bookkeeping_assistant
                  → 每日提醒「記帳組長」群組。
  時鐘 B 遲未首次聯繫：指派(assigned_at)後 M 天仍無 contact_date
                      → 每日提醒「該助理本人 + 記帳組長」。

任一逾 ESCALATE 天仍未動 → 加副知「合夥人」群組。

停錶：assigned_at 由 BookkeepingClient.save() 在指派那刻寫入；contact_date 由
助理發出前置收料連結（或手填聯繫紀錄）寫入。本模組只負責「掃描沒動的 + 寄催促」，
不改任何客戶資料。每位收件人每天彙整成「一封 digest」，不一案一封轟炸。

「事件」由 signal 處理（簽署→建客戶）；「時間流逝沒人動」沒有事件可掛，
只能靠這支每日 Celery beat 掃描——這正是舊系統按鈕做不到、要補的那一塊。
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone

logger = logging.getLogger(__name__)

# 門檻（日曆天）寫 settings 可調；此處為 fallback 預設。
ASSIGN_DAYS = getattr(settings, 'ONBOARDING_SLA_ASSIGN_DAYS', 2)
CONTACT_DAYS = getattr(settings, 'ONBOARDING_SLA_CONTACT_DAYS', 3)
ESCALATE_DAYS = getattr(settings, 'ONBOARDING_SLA_ESCALATE_DAYS', 7)

GROUP_LEAD_NAME = getattr(settings, 'ONBOARDING_SLA_GROUP_LEAD_GROUP', 'management')
PARTNER_NAME = getattr(settings, 'ONBOARDING_SLA_PARTNER_GROUP', 'CPA')

EMAIL_TEMPLATE_CODE = 'bookkeeping_onboarding_sla_digest'


def _onboarding_base_qs():
    """走過 onboarding 的承接中客戶。

    用 client_source 不為空把「舊有資料」擋掉——只有從工商斷點 / 轉入流程
    建檔的客戶才有 client_source，避免歷史客戶因沒指派助理而被誤掃成逾期。
    """
    from modules.bookkeeping.models import BookkeepingClient
    return BookkeepingClient.objects.filter(
        is_deleted=False,
        acceptance_status=BookkeepingClient.AcceptanceStatus.ACTIVE,
        client_source__isnull=False,
    )


def _group_recipients(group_name):
    """回傳該 Django Group 內可收信的 active User 清單。"""
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        logger.warning('SLA 角色群組不存在：%s（請在 admin 建立並指派成員）', group_name)
        return []
    return list(
        group.user_set.filter(is_active=True)
        .exclude(email='').exclude(email__isnull=True)
    )


def scan(today=None):
    """掃描兩段時鐘逾期的客戶。

    回傳 {'assign': [item, ...], 'contact': [item, ...]}；
    item = {'client', 'days_overdue', 'escalated'}。
    """
    today = today or timezone.now().date()
    assign_cutoff = today - timedelta(days=ASSIGN_DAYS)
    contact_cutoff = today - timedelta(days=CONTACT_DAYS)
    base = _onboarding_base_qs()

    assign_items = []
    for c in base.filter(
        bookkeeping_assistant__isnull=True,
        created_at__date__lte=assign_cutoff,
    ).order_by('created_at'):
        overdue = (today - c.created_at.date()).days
        assign_items.append({
            'client': c,
            'days_overdue': overdue,
            'escalated': overdue >= ESCALATE_DAYS,
        })

    contact_items = []
    for c in base.filter(
        bookkeeping_assistant__isnull=False,
        contact_date__isnull=True,
        assigned_at__isnull=False,
        assigned_at__lte=contact_cutoff,
    ).select_related('bookkeeping_assistant', 'bookkeeping_assistant__user').order_by('assigned_at'):
        overdue = (today - c.assigned_at).days
        contact_items.append({
            'client': c,
            'days_overdue': overdue,
            'escalated': overdue >= ESCALATE_DAYS,
        })

    return {'assign': assign_items, 'contact': contact_items}


def _user_display(user):
    name = ''
    if hasattr(user, 'get_full_name'):
        name = (user.get_full_name() or '').strip()
    return name or getattr(user, 'username', '') or user.email


def _bucket(buckets, user):
    return buckets.setdefault(
        user.pk, {'user': user, 'assign': {}, 'contact': {}}
    )


def run(today=None, dry_run=False):
    """掃描 + 依收件人彙整 + 寄送 digest。回傳摘要 dict 供 command 記錄。"""
    from core.notifications.services import EmailService

    today = today or timezone.now().date()
    result = scan(today)
    leads = _group_recipients(GROUP_LEAD_NAME)
    partners = _group_recipients(PARTNER_NAME)

    # 依收件人分桶；用 dict 以 client.pk 為鍵自動去重
    # （同一案可能因「組長 + 合夥人」或「助理 + 組長」被加多次）。
    buckets = {}

    for item in result['assign']:
        for u in leads:
            _bucket(buckets, u)['assign'][item['client'].pk] = item
        if item['escalated']:
            for u in partners:
                _bucket(buckets, u)['assign'][item['client'].pk] = item

    for item in result['contact']:
        assistant = item['client'].bookkeeping_assistant
        assistant_user = getattr(assistant, 'user', None)
        if assistant_user and assistant_user.is_active and assistant_user.email:
            _bucket(buckets, assistant_user)['contact'][item['client'].pk] = item
        for u in leads:
            _bucket(buckets, u)['contact'][item['client'].pk] = item
        if item['escalated']:
            for u in partners:
                _bucket(buckets, u)['contact'][item['client'].pk] = item

    sent = 0
    recipients_detail = []
    for b in buckets.values():
        assign_list = sorted(b['assign'].values(), key=lambda i: -i['days_overdue'])
        contact_list = sorted(b['contact'].values(), key=lambda i: -i['days_overdue'])
        if not assign_list and not contact_list:
            continue

        context = {
            'recipient_name': _user_display(b['user']),
            'assign_items': [{
                'name': i['client'].name,
                'tax_id': i['client'].tax_id or '',
                'days_overdue': i['days_overdue'],
                'escalated': i['escalated'],
            } for i in assign_list],
            'contact_items': [{
                'name': i['client'].name,
                'tax_id': i['client'].tax_id or '',
                'assistant': (
                    i['client'].bookkeeping_assistant.name
                    if i['client'].bookkeeping_assistant else ''
                ),
                'days_overdue': i['days_overdue'],
                'escalated': i['escalated'],
            } for i in contact_list],
            'assign_count': len(assign_list),
            'contact_count': len(contact_list),
            'today': today.isoformat(),
        }
        recipients_detail.append(
            (b['user'].email, len(assign_list), len(contact_list))
        )
        if not dry_run:
            ok = EmailService.send_email(
                EMAIL_TEMPLATE_CODE, [b['user'].email], context
            )
            if ok:
                sent += 1
        else:
            sent += 1

    return {
        'assign_overdue': len(result['assign']),
        'contact_overdue': len(result['contact']),
        'recipients': len(recipients_detail),
        'sent': sent,
        'details': recipients_detail,
        'no_lead': not leads,
        'no_partner': not partners,
    }
