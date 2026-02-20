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
