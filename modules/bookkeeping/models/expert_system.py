from django.db import models
from django.utils.translation import gettext_lazy as _
from .bookkeeping_client import BookkeepingClient

class ClientRuleSetting(models.Model):
    """客戶專屬的規則設定 (覆蓋預設值)"""
    client = models.ForeignKey(BookkeepingClient, on_delete=models.CASCADE, related_name='expert_rule_settings', verbose_name=_('客戶'))
    rule_code = models.CharField(max_length=50, verbose_name=_('規則代碼'))
    custom_threshold = models.FloatField(verbose_name=_('客製化閾值'), null=True, blank=True, help_text=_('若為空值則使用系統預設閾值'))
    is_active = models.BooleanField(default=True, verbose_name=_('是否啟用此規則'))

    class Meta:
        verbose_name = _('客戶專屬規則設定')
        verbose_name_plural = _('客戶專屬規則設定')
        unique_together = ('client', 'rule_code')

    def __str__(self):
        status = "啟用" if self.is_active else "停用"
        return f"[{self.client.company.name}] {self.rule_code} - {status}"


class RuleAlert(models.Model):
    """異常警報紀錄"""
    STATUS_CHOICES = (
        ('UNHANDLED', _('未處理')),
        ('NOTIFIED', _('已通知')),
        ('IGNORED', _('忽略')),
    )

    client = models.ForeignKey(BookkeepingClient, on_delete=models.CASCADE, related_name='rule_alerts', verbose_name=_('客戶'))
    # 這裡關聯到發生的期別，考慮到 Aura 有 BookkeepingPeriod / TaxFilingPeriod 等多種期別，
    # 為了保持彈性，這裡我們先用年份與期別的字串來記錄，或者關聯到具體的 BookkeepingPeriod。
    # 從 models.__init__.py 可以看到有 BookkeepingPeriod。
    period = models.ForeignKey('BookkeepingPeriod', on_delete=models.CASCADE, related_name='rule_alerts', verbose_name=_('帳務期別'), null=True, blank=True)
    
    rule_code = models.CharField(max_length=50, verbose_name=_('規則代碼'))
    alert_message = models.TextField(verbose_name=_('警報訊息'))
    actual_value = models.FloatField(verbose_name=_('實際數值'), null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNHANDLED', verbose_name=_('處理狀態'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('建立時間'))
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('處理時間'))
    handled_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_rule_alerts', verbose_name=_('處理人員'))

    class Meta:
        verbose_name = _('專家系統警報紀錄')
        verbose_name_plural = _('專家系統警報紀錄')
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.client.company.name}] {self.rule_code} - {self.get_status_display()}"
