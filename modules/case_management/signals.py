"""案件管理通知 signals (MVP)

此 MVP 版本只寫入 CaseNotificationLog 與更新 last_activity_at；
實際 Email 寄送與站內通知對接 core/notifications，待整合。
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    Case, CaseReply, CaseAccessToken,
    CaseNotificationPreference, CaseNotificationLog,
)


@receiver(post_save, sender=Case)
def notify_on_case_created(sender, instance: Case, created, **kwargs):
    if not created:
        return
    if instance.source in (Case.Source.CLIENT_PORTAL, Case.Source.LINE_API, Case.Source.EMAIL):
        recipients = [instance.owner] + list(instance.collaborators.all())
        for user in recipients:
            _enqueue_internal(instance, CaseNotificationLog.Event.NEW_CASE, user)
    elif instance.source == Case.Source.INTERNAL and instance.external_contact_email:
        _enqueue_external(instance, CaseNotificationLog.Event.NEW_CASE, instance.external_contact_email)


@receiver(post_save, sender=CaseReply)
def notify_on_reply_created(sender, instance: CaseReply, created, **kwargs):
    if not created or instance.is_system_log:
        return

    case = instance.case
    case.last_activity_at = timezone.now()
    case.save(update_fields=['last_activity_at', 'updated_at'])

    if instance.author_type == CaseReply.AuthorType.INTERNAL:
        if case.external_contact_email:
            _enqueue_external(case, CaseNotificationLog.Event.NEW_REPLY, case.external_contact_email)
    elif instance.author_type == CaseReply.AuthorType.EXTERNAL:
        for user in [case.owner] + list(case.collaborators.all()):
            _enqueue_internal(case, CaseNotificationLog.Event.NEW_REPLY, user)


@receiver(pre_save, sender=Case)
def detect_status_change(sender, instance: Case, **kwargs):
    if not instance.pk:
        return
    try:
        old = Case.objects.get(pk=instance.pk)
    except Case.DoesNotExist:
        return
    if old.status != instance.status:
        instance._status_changed_from = old.status


@receiver(post_save, sender=Case)
def notify_on_status_change(sender, instance: Case, created, **kwargs):
    if created:
        return
    old_status = getattr(instance, '_status_changed_from', None)
    if not old_status:
        return

    CaseReply.objects.create(
        case=instance,
        author_type=CaseReply.AuthorType.SYSTEM,
        external_channel=CaseReply.Channel.SYSTEM,
        is_system_log=True,
        content=f"狀態變更：{dict(Case.Status.choices).get(old_status)} → {instance.get_status_display()}",
    )

    for user in [instance.owner] + list(instance.collaborators.all()):
        _enqueue_internal(instance, CaseNotificationLog.Event.STATUS_CHANGE, user)
    if instance.external_contact_email:
        _enqueue_external(instance, CaseNotificationLog.Event.STATUS_CHANGE, instance.external_contact_email)


def daily_followup_check():
    """供 management command / 排程任務呼叫"""
    today = timezone.now().date()
    due_cases = Case.objects.filter(
        needs_followup=True,
        next_followup_date__lte=today,
        status__in=[Case.Status.OPEN, Case.Status.WAITING_CLIENT, Case.Status.WAITING_INTERNAL],
        is_deleted=False,
    )
    for case in due_cases:
        _enqueue_internal(case, CaseNotificationLog.Event.FOLLOWUP_DUE, case.owner)


def _get_or_default_pref(user):
    try:
        return user.case_notification_pref
    except CaseNotificationPreference.DoesNotExist:
        return CaseNotificationPreference(user=user)


def _should_send_inapp(pref, event):
    return {
        CaseNotificationLog.Event.NEW_CASE: pref.inapp_on_new_case,
        CaseNotificationLog.Event.NEW_REPLY: pref.inapp_on_new_reply,
        CaseNotificationLog.Event.STATUS_CHANGE: pref.inapp_on_status_change,
    }.get(event, True)


def _should_send_email(pref, event):
    return {
        CaseNotificationLog.Event.NEW_CASE: pref.email_on_new_case,
        CaseNotificationLog.Event.NEW_REPLY: pref.email_on_new_reply,
        CaseNotificationLog.Event.STATUS_CHANGE: pref.email_on_status_change,
        CaseNotificationLog.Event.FOLLOWUP_DUE: pref.email_on_followup_due,
    }.get(event, True)


def _enqueue_internal(case, event, recipient_user):
    pref = _get_or_default_pref(recipient_user)
    if _should_send_inapp(pref, event):
        CaseNotificationLog.objects.create(
            case=case, event=event, channel=CaseNotificationLog.Channel.INAPP,
            recipient_user=recipient_user,
            status=CaseNotificationLog.Status.QUEUED,
        )
    if _should_send_email(pref, event):
        CaseNotificationLog.objects.create(
            case=case, event=event, channel=CaseNotificationLog.Channel.EMAIL,
            recipient_user=recipient_user, recipient_email=recipient_user.email or '',
            status=CaseNotificationLog.Status.QUEUED,
        )
        # TODO: 對接 core/notifications 的 Email 寄送（含批次合併）


def _enqueue_external(case, event, recipient_email):
    _get_or_issue_token(case, recipient_email)
    CaseNotificationLog.objects.create(
        case=case, event=event, channel=CaseNotificationLog.Channel.EMAIL,
        recipient_email=recipient_email,
        status=CaseNotificationLog.Status.QUEUED,
    )
    # TODO: 寄送 Email 含 magic link


def _get_or_issue_token(case, email, valid_days=30):
    existing = case.access_tokens.filter(
        email=email, revoked_at__isnull=True, expires_at__gt=timezone.now(),
    ).first()
    if existing:
        return existing
    return CaseAccessToken.issue(case=case, email=email, valid_days=valid_days)
