"""
Bookkeeping 模組 signal 集中管理。

設計原則
========
1. 所有 signal 集中在此檔案，方便追蹤「主檔變更會觸發什麼副作用」
2. 「主檔成立 → 子檔必須成立」的關係用 signal 實作
3. 失敗時直接 raise，由外層 transaction（ATOMIC_REQUESTS / @transaction.atomic）負責 rollback
4. 用 get_or_create 確保 idempotency：signal 重跑、資料還原時不會重複建立

註冊位置
========
modules/bookkeeping/apps.py 的 ready() 會 import 此模組。
"""

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .convenience_bag_log import ConvenienceBagLog
from .bookkeeping_client import BookkeepingClient, DEFAULT_PORTAL_PASSWORD
from .business_registration import BusinessRegistration
from .business_tax import TaxFilingSetting
from .income_tax import (
    IncomeTaxSetting,
    IncomeTaxYear,
    ProvisionalTax,
    WithholdingTax,
    DividendTax,
    IncomeTaxFiling,
)
from .progress import BookkeepingSetting


# =============================================================================
# Customer 同步
# =============================================================================
@receiver(post_save, sender='basic_data.Customer')
def sync_customer_to_bookkeeping_clients(sender, instance, **kwargs):
    """
    Customer 更新時，同步共用欄位到所有關聯的 BookkeepingClient。

    用 .update() 直接更新避免觸發 BookkeepingClient.post_save 造成迴圈。
    登記模組保持快照，不在此同步範圍內。
    """
    if instance.is_deleted:
        return
    instance.bookkeeping_clients.filter(is_deleted=False).update(
        tax_id=instance.tax_id,
        name=instance.name,
        line_id=instance.line_id,
        room_id=instance.room_id,
        contact_person=instance.contact_person,
        phone=instance.phone,
        mobile=instance.mobile,
        email=instance.email,
        correspondence_address=instance.correspondence_address,
        registered_address=instance.registered_address,
    )


# =============================================================================
# BookkeepingClient 建立 → 自動建子檔
# =============================================================================
@receiver(post_save, sender=BookkeepingClient)
def auto_create_business_registration(sender, instance, created, **kwargs):
    """新增 BookkeepingClient 時自動建立 BusinessRegistration（商業登記）"""
    if created:
        BusinessRegistration.objects.get_or_create(client=instance)


@receiver(post_save, sender=BookkeepingClient)
def auto_create_tax_filing_setting(sender, instance, created, **kwargs):
    """
    新增 BookkeepingClient 時一律建立 TaxFilingSetting（比照 IncomeTaxSetting）。

    可見性由 view 端以 service_type 即時判斷，不再以「子檔是否存在」當開關，
    因此每位客戶都先備妥設定檔，服務型態日後切換進營業人時不會缺子檔。

    form_type 預設值仍依建立當下的 service_type 推導（之後可在設定卡片手動調整）：
    - MIXED_DIRECT / MIXED_RATIO → 403 表
    - 其餘（含 VAT_BUSINESS）→ 401 表
    """
    if not created:
        return

    mixed = (
        BookkeepingClient.ServiceType.MIXED_DIRECT,
        BookkeepingClient.ServiceType.MIXED_RATIO,
    )
    if instance.service_type in mixed:
        form_type = TaxFilingSetting.FormType.FORM_403
    else:
        form_type = TaxFilingSetting.FormType.FORM_401

    TaxFilingSetting.objects.get_or_create(
        client=instance,
        defaults={'form_type': form_type},
    )


@receiver(post_save, sender=BookkeepingClient)
def auto_create_income_tax_setting(sender, instance, created, **kwargs):
    """新增 BookkeepingClient 時自動建立 IncomeTaxSetting（所得稅設定）"""
    if created:
        IncomeTaxSetting.objects.get_or_create(client=instance)


@receiver(post_save, sender=BookkeepingClient)
def auto_create_bookkeeping_setting(sender, instance, created, **kwargs):
    """新增 BookkeepingClient 時自動建立 BookkeepingSetting（記帳設定）"""
    if created:
        BookkeepingSetting.objects.get_or_create(client=instance)


@receiver(post_save, sender=BookkeepingClient)
def sync_client_portal_user(sender, instance, created, **kwargs):
    """
    BookkeepingClient 存檔時，自動建立或更新 client portal 登入帳號。

    - 軟刪除：停用關聯帳號
    - 無 tax_id：跳過（無法產生 username）
    - 未綁定帳號：建立新 User（初始密碼 = DEFAULT_PORTAL_PASSWORD）
    - 已綁定帳號：同步 username / first_name / email（不覆蓋密碼）

    失敗 raise 由外層 atomic 處理 rollback。
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if instance.is_deleted:
        if instance.user_id:
            User.objects.filter(pk=instance.user_id, is_active=True).update(is_active=False)
        return

    if not instance.tax_id:
        return

    username = str(instance.tax_id).strip()

    if not instance.user:
        # 先看 User 是否已存在（保 idempotent：重複 save 不會重建）
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                password=DEFAULT_PORTAL_PASSWORD,
                role='EXTERNAL',
                first_name=instance.name[:30],
                is_staff=False,
                is_superuser=False,
                email=instance.email or '',
            )
        type(instance).objects.filter(pk=instance.pk).update(user=user)
        instance.user = user  # 同步 in-memory 避免後續判斷再走進這分支
    else:
        user = instance.user
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.first_name != instance.name[:30]:
            user.first_name = instance.name[:30]
            changed = True
        email = instance.email or ''
        if user.email != email:
            user.email = email
            changed = True
        if changed:
            user.save()


# =============================================================================
# IncomeTaxYear 建立 → 自動建 5 個子項目
# =============================================================================
@receiver(post_save, sender=IncomeTaxYear)
def auto_create_income_tax_items(sender, instance, created, **kwargs):
    """
    新增 IncomeTaxYear 時自動建立 5 個子項目：
    暫繳稅、扣繳稅、股利稅、結算申報、媒體檔解析資料
    """
    if not created:
        return

    ProvisionalTax.objects.get_or_create(year_record=instance)
    WithholdingTax.objects.get_or_create(year_record=instance)
    DividendTax.objects.get_or_create(year_record=instance)
    IncomeTaxFiling.objects.get_or_create(year_record=instance)
    # 延遲 import 避免循環依賴
    from .income_tax_media import IncomeTaxMediaData
    IncomeTaxMediaData.objects.get_or_create(year_record=instance)


# =============================================================================
# ConvenienceBagLog 變動 → 同步 BookkeepingClient 摘要欄位
# =============================================================================
@receiver([post_save, post_delete], sender=ConvenienceBagLog)
def update_bookkeeping_client_convenience_bag_fields(sender, instance, **kwargs):
    """
    ConvenienceBagLog 新增/更新/刪除時，更新 BookkeepingClient 的
    last_convenience_bag_date 與 last_convenience_bag_qty。
    僅 update_fields 指定欄位，避免覆蓋其他正在編輯的資訊。
    """
    client = instance.client
    latest_log = client.convenience_bag_logs.order_by('-date', '-created_at').first()

    if latest_log:
        client.last_convenience_bag_date = latest_log.date
        client.last_convenience_bag_qty = latest_log.quantity
    else:
        client.last_convenience_bag_date = None
        client.last_convenience_bag_qty = None

    client.save(update_fields=['last_convenience_bag_date', 'last_convenience_bag_qty'])
