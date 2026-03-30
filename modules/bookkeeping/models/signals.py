from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .convenience_bag_log import ConvenienceBagLog

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

    # Needs a tax ID and a business password to act as an account
    if not instance.tax_id or not instance.business_password:
        return
        
    username = str(instance.tax_id).strip()
    password = str(instance.business_password).strip()
    
    if not instance.user:
        # Create a new User
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                role='EXTERNAL',
                first_name=instance.name[:30],
                is_staff=False,
                is_superuser=False,
                email=instance.email or ''
            )
            # Use raw query or update to avoid triggering infinite recursion
            type(instance).objects.filter(pk=instance.pk).update(user=user)
        except Exception as e:
            print(f"Failed to auto-create client portal user for {username}: {str(e)}")
    else:
        # User already exists, update username and password if they differ
        user = instance.user
        changed = False
        
        if user.username != username:
            user.username = username
            changed = True
            
        if not user.check_password(password):
            user.set_password(password)
            changed = True
            
        if user.first_name != instance.name[:30]:
            user.first_name = instance.name[:30]
            changed = True
            
        if changed:
            user.save()
