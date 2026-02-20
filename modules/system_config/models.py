from django.db import models
from django.contrib.auth.models import Group

class MenuItem(models.Model):
    """
    Represents a dynamic menu item in the sidebar.
    Supports hierarchy (parent-child) and role-based visibility via Groups.
    """
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name="父層選單"
    )
    title = models.CharField("顯示名稱", max_length=100)
    url_name = models.CharField("URL 名稱", max_length=100, blank=True, help_text="Django URL pattern name (e.g. 'dashboard') or absolute URL")
    icon_svg = models.TextField("SVG 圖示", blank=True, help_text="Paste the full <svg> code here")
    order = models.PositiveIntegerField("排序", default=0)
    
    # Permissions: If empty, visible to everyone (or authenticated only).
    # If set, user must belong to at least one of these groups.
    roles = models.ManyToManyField(
        Group, 
        blank=True, 
        verbose_name="可見角色",
        help_text="留空則對所有登入使用者可見"
    )

    is_active = models.BooleanField("是否啟用", default=True)

    class Meta:
        verbose_name = "選單項目"
        verbose_name_plural = "選單管理"
        ordering = ['order']

    def __str__(self):
        return f"{'-- ' if self.parent else ''}{self.title}"

class SystemParameter(models.Model):
    """
    Stores system configuration parameters (e.g., Email settings, API keys).
    """
    GROUP_CHOICES = (
        ('email', 'Email'),
        ('payment', 'Payment (ECPay)'),
        ('line', 'Line'),
        ('ai', 'AI (Gemini)'),
        ('other', 'Other'),
    )

    key = models.CharField("參數鍵名", max_length=50, unique=True, help_text="Unique key, e.g. EMAIL_HOST")
    value = models.TextField("參數值", blank=True)
    description = models.CharField("描述", max_length=255, blank=True)
    is_secret = models.BooleanField("是否加密/隱藏", default=False, help_text="If true, value will be masked in UI")
    group = models.CharField("群組", max_length=20, choices=GROUP_CHOICES, default='other')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "系統參數"
        verbose_name_plural = "系統參數設定"
        ordering = ['group', 'key']

    def __str__(self):
        return f"{self.key} ({self.get_group_display()})"
