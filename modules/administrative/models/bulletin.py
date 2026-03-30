from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import BaseModel

class SystemBulletin(BaseModel):
    """系統公佈欄模型"""
    
    class StatusChoices(models.TextChoices):
        ACTIVE = 'active', _('生效')
        INACTIVE = 'inactive', _('失效')
        
    class ImportanceChoices(models.TextChoices):
        HIGH = 'high', _('高')
        MEDIUM = 'medium', _('中')
        LOW = 'low', _('低')
        
    importance_level = models.CharField(
        _('重要等級'),
        max_length=20,
        choices=ImportanceChoices.choices,
        default=ImportanceChoices.LOW
    )
        
    publish_date = models.DateField(
        _('日期'), 
        default=timezone.now,
        help_text=_('公佈日期')
    )
    subject = models.CharField(
        _('主題'), 
        max_length=200
    )
    content = models.TextField(
        _('相關說明')
    )
    status = models.CharField(
        _('狀態'), 
        max_length=20, 
        choices=StatusChoices.choices, 
        default=StatusChoices.ACTIVE
    )

    class Meta:
        verbose_name = _('系統公佈欄')
        verbose_name_plural = _('系統公佈欄')
        ordering = ['-publish_date', '-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.publish_date} - {self.subject}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('administrative:system_bulletin_update', kwargs={'pk': self.pk})
