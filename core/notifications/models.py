from django.db import models
from django.utils.translation import gettext_lazy as _
# from ckeditor.fields import RichTextField  # Assuming ckeditor is available or use TextField

class EmailTemplate(models.Model):
    code = models.CharField(_("Code"), max_length=100, unique=True, help_text=_("Unique identifier for calling this template in code"))
    name = models.CharField(_("Name"), max_length=255)
    subject = models.CharField(_("Subject Template"), max_length=255, help_text=_("Supports Jinja2 syntax like {{ name }}"))
    body_html = models.TextField(_("Body (HTML)"), help_text=_("Supports Jinja2 syntax"))
    is_active = models.BooleanField(_("Active"), default=True)
    
    # Optional connection to a specific model to filter templates
    model_content_type = models.ForeignKey(
        'contenttypes.ContentType', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Applicable Model")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = _("Email Template")
        verbose_name_plural = _("Email Templates")

class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('scheduled', _('Scheduled')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
    )

    recipient = models.EmailField(_("Recipient"))
    subject = models.CharField(_("Subject"), max_length=255)
    body = models.TextField(_("Body"), blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Template"))
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(_("Error Message"), blank=True)
    scheduled_at = models.DateTimeField(_("Scheduled At"), null=True, blank=True)
    sent_at = models.DateTimeField(_("Sent At"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To: {self.recipient} - {self.subject} ({self.status})"

    class Meta:
        verbose_name = _("Email Log")
        verbose_name_plural = _("Email Logs")
        ordering = ['-created_at']

class LineMessageTemplate(models.Model):
    MESSAGE_TYPES = (
        ('text', _('Text Message')),
        ('flex', _('Flex Message')),
    )

    code = models.CharField(_("Code"), max_length=100, unique=True, help_text=_("Unique identifier"))
    name = models.CharField(_("Name"), max_length=255)
    message_type = models.CharField(_("Type"), max_length=20, choices=MESSAGE_TYPES, default='text')
    
    text_content = models.TextField(_("Text Content"), blank=True, help_text=_("For Text Messages. Supports Jinja2 syntax."))
    flex_content_json = models.TextField(_("Flex JSON"), blank=True, help_text=_("For Flex Messages. Valid JSON structure."))
    
    # Optional connection to a specific model to filter templates
    model_content_type = models.ForeignKey(
        'contenttypes.ContentType', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Applicable Model")
    )
    
    is_active = models.BooleanField(_("Active"), default=True)
    
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = _("Line Template")
        verbose_name_plural = _("Line Templates")

class LineMessageLog(models.Model):
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
    )

    recipient_line_id = models.CharField(_("Line User ID"), max_length=100)
    template = models.ForeignKey(LineMessageTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(_("Error Message"), blank=True)
    sent_at = models.DateTimeField(_("Sent At"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To: {self.recipient_line_id} - {self.template} ({self.status})"

    class Meta:
        verbose_name = _("Line Log")
        verbose_name_plural = _("Line Logs")
        ordering = ['-created_at']


class LineEventLog(models.Model):
    """LINE inbound 事件紀錄（append-only）。

    收 message（只記文字 text）/ join / follow 三類事件，作為知識庫萃取素材、
    提問歷史與 userID·roomID 撈取來源。

    刻意不繼承 BaseModel：log 永不修改，不需要 HistoricalRecords / is_deleted，
    避免每筆寫入被歷史表翻倍。去重靠 webhook_event_id（LINE 重送時不變）。
    """
    EVENT_TYPES = (
        ('message', 'Message'),
        ('join', 'Join'),
        ('follow', 'Follow'),
    )

    webhook_event_id = models.CharField(_("事件 ID"), max_length=64, unique=True)
    event_type = models.CharField(_("事件類型"), max_length=20, choices=EVENT_TYPES)
    sent_at = models.DateTimeField(_("發生時間"), db_index=True)

    source_type = models.CharField(_("來源類型"), max_length=10)  # user / group / room
    room_id = models.CharField(_("RoomID"), max_length=64, blank=True, db_index=True)
    sender_user_id = models.CharField(_("發話者 UserID"), max_length=64, blank=True, db_index=True)

    # 目前只寫 'text'（非文字不記錄）；join/follow 空。欄位保留供未來擴建
    message_type = models.CharField(_("訊息類型"), max_length=20, blank=True)
    text = models.TextField(_("文字內容"), blank=True)
    # text 訊息填；保留供未來非文字擴建
    line_message_id = models.CharField(_("訊息 ID"), max_length=64, blank=True)

    customer = models.ForeignKey(
        'basic_data.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, db_index=True, verbose_name=_("對應客戶"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("LINE 事件紀錄")
        verbose_name_plural = _("LINE 事件紀錄")
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['room_id', 'sent_at']),
            models.Index(fields=['sender_user_id', 'sent_at']),
        ]

    def __str__(self):
        who = self.room_id or self.sender_user_id or '?'
        return f"[{self.event_type}] {who} @ {self.sent_at:%Y-%m-%d %H:%M}"
