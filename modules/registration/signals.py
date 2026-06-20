from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Progress, CompanyFiling, FilingHistory, VATEntityChange
from django.utils import timezone

@receiver(post_save, sender=Progress)
def auto_create_related_services(sender, instance, created, **kwargs):
    """
    Automatically create related service forms based on selected case types in Progress.
    """
    case_types = instance.case_type
    if not isinstance(case_types, list):
        return

    # 1. Company Law 22-1 Automation
    # Check if any row in quotation_data has is_company_law_22_1 set to True
    quotation_data = instance.quotation_data
    should_create_22_1 = any(
        isinstance(item, dict) and item.get('is_company_law_22_1') is True 
        for item in quotation_data
    ) if isinstance(quotation_data, list) else False

    if should_create_22_1:
        # 1. Ensure CompanyFiling (Parent) exists for this UBN
        ubn = instance.unified_business_no
        filing_parent, created_parent = CompanyFiling.objects.get_or_create(
            unified_business_no=ubn,
            defaults={
                'company_name': instance.company_name,
                'line_id': instance.line_id,
                'room_id': instance.room_id,
                'main_contact': instance.main_contact,
                'mobile': instance.mobile,
                'phone': instance.phone,
                'address': instance.address,
                'note': f"由登記進度表 {instance.registration_no} 自動建立基本資料"
            }
        ) if ubn else (None, False)
        
        if filing_parent:
            # 2. Check if a FilingHistory (Child) already exists FOR THIS SPECIFIC PROGRESS CASE
            history_exists = FilingHistory.objects.filter(
                company_filing=filing_parent,
                registration_no=instance.registration_no
            ).exists()
            
            if not history_exists:
                FilingHistory.objects.create(
                    company_filing=filing_parent,
                    registration_no=instance.registration_no,
                    year=timezone.now().year,
                    category=FilingHistory.FilingCategory.ANNUAL,  # Default to ANNUAL
                    filing_date=timezone.now().date()
                )

    # 2. AML Check Automation
    should_create_aml = any(
        isinstance(item, dict) and item.get('is_money_laundering_check') is True 
        for item in quotation_data
    ) if isinstance(quotation_data, list) else False

    if should_create_aml:
        from .models.client_assessment import ClientAssessment
        from .models.case_assessment import CaseAssessment
        
        # 1. Ensure ClientAssessment exists
        ubn = instance.unified_business_no
        client_assessment, created_client = ClientAssessment.objects.get_or_create(
            unified_business_no=ubn,
            defaults={
                'company_name': instance.company_name,
                'line_id': instance.line_id,
                'room_id': instance.room_id,
                'main_contact': instance.main_contact,
                'mobile': instance.mobile,
                'phone': instance.phone,
                'address': instance.address,
            }
        ) if ubn else (None, False)

        if client_assessment:
            # 2. Check if CaseAssessment already exists for this progress case
            assessment_exists = CaseAssessment.objects.filter(
                registration_no=instance.registration_no
            ).exists()
            
            if not assessment_exists:
                CaseAssessment.objects.create(
                    client_assessment=client_assessment,
                    registration_no=instance.registration_no,
                    date=timezone.now().date(),
                    company_name=instance.company_name,
                    unified_business_no=instance.unified_business_no,
                    line_id=instance.line_id,
                    room_id=instance.room_id,
                    main_contact=instance.main_contact,
                    mobile=instance.mobile,
                    phone=instance.phone,
                    address=instance.address
                )

    # 3. Shareholder Register / Equity Transaction Automation
    should_create_equity_tx = any(
        isinstance(item, dict) and item.get('is_shareholder_list_change') is True 
        for item in quotation_data
    ) if isinstance(quotation_data, list) else False

    if should_create_equity_tx:
        from .models import ShareholderRegister, EquityTransaction
        
        # 1. Ensure ShareholderRegister (Parent) exists
        ubn = instance.unified_business_no
        register, created_reg = ShareholderRegister.objects.get_or_create(
            unified_business_no=ubn,
            defaults={
                'company_name': instance.company_name,
                'line_id': instance.line_id,
                'room_id': instance.room_id,
            }
        ) if ubn else (None, False)

        if register:
            # 2. Check if EquityTransaction already exists for this progress case
            tx_exists = EquityTransaction.objects.filter(
                registration_no=instance.registration_no
            ).exists()
            
            if not tx_exists:
                EquityTransaction.objects.create(
                    shareholder_register=register,
                    registration_no=instance.registration_no,
                    shareholder_name="[自動建立]",
                    shareholder_id_number="PENDING",
                    transaction_date=timezone.now().date(),
                    organization_type='LTD',
                    transaction_reason='OTHER_INCREASE',
                    stock_type='COMMON',
                    share_count=0,
                    unit_price=0,
                    total_amount=0,
                    note=f"由登記進度表 {instance.registration_no} 自動建立"
                )

    # 4. VAT Entity Change Automation
    should_create_vat_change = any(
        isinstance(item, dict) and item.get('is_business_entity_change') is True 
        for item in quotation_data
    ) if isinstance(quotation_data, list) else False

    if should_create_vat_change:
        from .models import VATEntityChange
        
        # 4a. Update Progress case_type if needed
        if 'business_change' not in case_types:
            case_types.append('business_change')
            # Use update() to avoid triggering post_save recursively if not careful, 
            # but since we are in post_save, we should be careful.
            # Actually, standard practice here is to use instance.save(update_fields=['case_type']) 
            # but we must avoid infinite loops.
            # A simpler way is to update the list and let it be saved if we are early enough, 
            # but post_save is too late for direct instance.save() without recursion protection.
            Progress.objects.filter(pk=instance.pk).update(case_type=case_types)

        # 4b. Ensure VATEntityChange exists for this progress case
        VATEntityChange.objects.get_or_create(
            registration_no=instance.registration_no,
            defaults={
                'unified_business_no': instance.unified_business_no or "",
                'company_name': instance.company_name or "",
                'tax_id': "", # To be filled
                'registered_address': instance.address or "",
                'assistant_name': "", # To be filled
                'email': "pending@example.com", # EmailField needs a valid format or blank=True
                'case_types': ['business_change'],
                'note': f"由登記進度表 {instance.registration_no} 自動建立"
            }
        )

@receiver(post_save, sender=VATEntityChange)
def sync_vat_completion_to_progress(sender, instance, **kwargs):
    """
    Sync VATEntityChange completion status back to the main Progress record.
    If VAT change is completed, move Progress to CLOSED.
    """
    if instance.registration_no and instance.is_completed:
        from .models import Progress
        # Update progress status to CLOSED (4) if it's not already closed or higher
        Progress.objects.filter(
            registration_no=instance.registration_no,
            progress_status__lt=Progress.ProgressStatus.CLOSED
        ).update(progress_status=Progress.ProgressStatus.CLOSED)


def _has_setup_service(progress):
    """報價單服務項目代碼/名稱以 3.01 開頭 = 公司登記設立。"""
    qd = progress.quotation_data
    if not isinstance(qd, list):
        return False
    for item in qd:
        if not isinstance(item, dict):
            continue
        for key in ('service_code', 'service_name'):
            if str(item.get(key) or '').strip().startswith('3.01'):
                return True
    return False


@receiver(post_save, sender=Progress)
def auto_create_engagement_draft(sender, instance, created, **kwargs):
    """工商案結案 + 報價含設立(3.01) → 自動建記帳委任書草稿。

    觸發時機：Progress 存檔，且進度=結案，且報價單有 3.01 開頭的服務項目。
    副作用：呼叫 bookkeeping service 建一筆 EngagementLetter 草稿（idempotent，
            同一案號已有委任書則略過）；開始委任日/email 留空待承辦補。
    跨模組經 service call（傳純值，不直接操作 bookkeeping model）。
    註：VATEntityChange 自動結案走 QuerySet.update() 不觸發本 signal，
        該情境由承辦於工商頁手動結案時補觸發。
    """
    if instance.progress_status != Progress.ProgressStatus.CLOSED:
        return
    if not _has_setup_service(instance):
        return
    from modules.bookkeeping.services.engagement_letter import create_draft_from_progress
    create_draft_from_progress(
        progress_no=instance.registration_no,
        company_name=instance.company_name,
        tax_id=instance.unified_business_no or '',
        contact_name=instance.main_contact or '',
        contact_phone=instance.mobile or instance.phone or '',
    )
