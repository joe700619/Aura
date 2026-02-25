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
