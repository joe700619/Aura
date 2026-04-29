from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .convenience_bag_log import ConvenienceBagLog


@receiver(post_save, sender='basic_data.Customer')
def sync_customer_to_bookkeeping_clients(sender, instance, **kwargs):
    """
    當 Customer 更新時，同步共用欄位到所有關聯的 BookkeepingClient。
    使用 .update() 避免觸發 BookkeepingClient.post_save 造成迴圈。
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

@receiver([post_save, post_delete], sender=ConvenienceBagLog)
def update_bookkeeping_client_convenience_bag_fields(sender, instance, **kwargs):
    """
    更新 BookkeepingClient 的 last_convenience_bag_date 與 last_convenience_bag_qty
    只要 ConvenienceBagLog 被新增、更新或刪除，就會觸發重新計算
    """
    client = instance.client
    latest_log = client.convenience_bag_logs.order_by('-date', '-created_at').first()
    
    if latest_log:
        client.last_convenience_bag_date = latest_log.date
        client.last_convenience_bag_qty = latest_log.quantity
    else:
        client.last_convenience_bag_date = None
        client.last_convenience_bag_qty = None
        
    # 只更新指定的欄位，避免覆蓋其他正在編輯的資訊
    client.save(update_fields=['last_convenience_bag_date', 'last_convenience_bag_qty'])

@receiver(post_save, sender='bookkeeping.BookkeepingClient')
def sync_client_portal_user(sender, instance, created, **kwargs):
    """
    當 BookkeepingClient 存檔時，自動建立或更新外部客戶登入的 User 帳號
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # 已軟刪除：停用關聯帳號並跳過
    if instance.is_deleted:
        if instance.user_id:
            User.objects.filter(pk=instance.user_id, is_active=True).update(is_active=False)
        return

    if not instance.tax_id:
        return

    username = str(instance.tax_id).strip()

    if not instance.user:
        # 初始密碼 = 統一編號
        try:
            user = User.objects.create_user(
                username=username,
                password=username,
                role='EXTERNAL',
                first_name=instance.name[:30],
                is_staff=False,
                is_superuser=False,
                email=instance.email or ''
            )
            type(instance).objects.filter(pk=instance.pk).update(user=user)
        except Exception as e:
            print(f"Failed to auto-create client portal user for {username}: {str(e)}")
    else:
        # 僅同步 username / email / first_name，不覆蓋使用者自行修改的密碼
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
