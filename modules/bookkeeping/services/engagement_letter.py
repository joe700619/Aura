"""記帳委任書：渲染、簽署投影、婉拒。

簽署成立＝投影：凍結快照 → 建 BookkeepingClient（未指派，自動進交接 SLA 收件匣）
→ 投影 ServiceFee（生效日＝開始委任日）→ 翻來源 Inquiry 為已成交。
與 intake→孤島、SLA 同哲學：未簽不生客戶、髒資料不落地。
"""
import logging

from django.db import transaction
from django.template import Context, Template
from django.utils import timezone

from ..models import BookkeepingClient, EngagementLetter, ServiceFee

logger = logging.getLogger(__name__)


def render_letter_html(letter: EngagementLetter) -> str:
    """用委任書採用的範本版本 + 本件資料渲染條款本文。

    預覽（公開頁待簽時）與簽署凍結都走這支，確保所見即所簽。
    """
    tpl = Template(letter.template_version.body_html)
    ctx = Context({
        'company_name': letter.company_name,
        'tax_id': letter.tax_id,
        'contact_name': letter.contact_name,
        'engagement_start_date': letter.engagement_start_date,
        'pricing_type': letter.get_pricing_type_display(),
        'service_fee': letter.service_fee,
        'ledger_fee': letter.ledger_fee,
        'billing_cycle': letter.get_billing_cycle_display(),
        'fee_note': letter.fee_note,
        'today': timezone.now().date(),
    })
    return tpl.render(ctx)


@transaction.atomic
def sign_letter(letter: EngagementLetter, ip=None, *, signature_file=None,
                signer_name='', signer_email='') -> BookkeepingClient:
    """客戶手寫簽名確認時呼叫。idempotent：已簽則直接回傳已建客戶。

    留歸屬證據：凍結內容快照 + 手寫簽名圖 + 簽署人自填姓名/Email + IP，
    證明是對方本人簽署（非僅持有連結點同意鈕）。
    """
    from django.core.files.base import ContentFile

    if letter.status == EngagementLetter.Status.SIGNED:
        return letter.created_client

    # ① 凍結快照（簽署那刻的渲染內容，永不重生）
    letter.rendered_snapshot = render_letter_html(letter)
    letter.status = EngagementLetter.Status.SIGNED
    letter.signed_at = timezone.now()
    letter.signer_ip = ip
    letter.signer_name = signer_name or ''
    letter.signer_email = signer_email or ''
    if signature_file is not None:
        sig_bytes = signature_file.read() if hasattr(signature_file, 'read') else signature_file
        letter.signature_image = ContentFile(sig_bytes, name='signature.png')

    # ② 建 / 連記帳客戶。有統編則 get_or_create（避免重複建檔）；無統編直接建。
    client_defaults = {
        'name': letter.company_name,
        'client_source': letter.client_source,
        'email': letter.contact_email,
        'contact_person': letter.contact_name,
        'phone': letter.contact_phone,
    }
    created = False
    if letter.tax_id:
        client, created = BookkeepingClient.objects.get_or_create(
            tax_id=letter.tax_id, is_deleted=False,
            defaults=client_defaults,
        )
    else:
        client = BookkeepingClient.objects.create(**client_defaults)
        created = True

    # ③ 投影 ServiceFee（只在新建客戶時，避免動到既有客戶的計費歷史）
    if created:
        ServiceFee.objects.create(
            client=client,
            service_fee=letter.service_fee,
            ledger_fee=letter.ledger_fee,
            billing_cycle=letter.billing_cycle,
            effective_date=letter.engagement_start_date,
            notes=letter.fee_note,
        )

    letter.created_client = client
    letter.save()

    # ④ 翻來源 Inquiry 為已成交（跨模組走 service）
    if letter.inquiry_id:
        from modules.case_management.services import mark_inquiry_converted
        mark_inquiry_converted(letter.inquiry_id)

    logger.info('記帳委任書簽署投影完成：letter=%s client=%s(created=%s)',
                letter.pk, client.pk, created)
    return client


def create_draft_from_progress(progress_no, company_name, tax_id='',
                               contact_name='', contact_phone='',
                               contact_email='') -> EngagementLetter:
    """工商案結案時，由 registration signal 呼叫，自動建記帳委任書草稿。

    idempotent：同一工商案號已有委任書（含已刪/已簽）則不重建。
    開始委任日與 email 留空，承辦補填後才發送（見 send view 的 guard）。
    費用預帶基礎方案。跨模組由 registration → 此 service 進入，傳純值不傳 model。
    """
    from django.conf import settings
    from ..models import EngagementLetterTemplate

    if EngagementLetter.objects.filter(progress_no=progress_no).exists():
        return None
    template = EngagementLetterTemplate.get_active()
    if not template:
        logger.warning('無使用中委任書範本，略過自動建草稿 progress=%s', progress_no)
        return None

    letter = EngagementLetter.objects.create(
        progress_no=progress_no,
        company_name=company_name,
        tax_id=tax_id or '',
        contact_name=contact_name or '',
        contact_phone=contact_phone or '',
        contact_email=contact_email or '',
        client_source=BookkeepingClient.ClientSource.OUR_FIRM,
        engagement_start_date=None,
        pricing_type=EngagementLetter.PricingType.BASE,
        service_fee=getattr(settings, 'BOOKKEEPING_BASE_MONTHLY_FEE', 2000),
        billing_cycle=ServiceFee.BillingCycle.BIMONTHLY,
        template_version=template,
        status=EngagementLetter.Status.DRAFT,
    )
    logger.info('結案自動建記帳委任書草稿：progress=%s letter=%s', progress_no, letter.pk)
    return letter


def decline_letter(letter: EngagementLetter, reason: str = '') -> None:
    """客戶婉拒。不建客戶；Inquiry 維持原狀由承辦決定是否標未成交。"""
    if letter.status in (EngagementLetter.Status.SIGNED,
                         EngagementLetter.Status.DECLINED):
        return
    letter.status = EngagementLetter.Status.DECLINED
    letter.decline_reason = reason
    letter.save(update_fields=['status', 'decline_reason', 'updated_at'])
