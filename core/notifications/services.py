import logging
from django.core.mail import send_mail
from django.utils import timezone
from django.template import Template, Context
from django.conf import settings
from .models import EmailTemplate, EmailLog, LineMessageTemplate, LineMessageLog

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_email(template_code: str, recipients: list, context: dict, schedule_time=None, attachments=None) -> bool:
        """
        Sends, or schedules, an email using a database template.
        """
        try:
            template = EmailTemplate.objects.get(code=template_code, is_active=True)
        except EmailTemplate.DoesNotExist:
            logger.error(f"Email template '{template_code}' not found or inactive.")
            return False

        # Render Subject and Body
        try:
            subject_tpl = Template(template.subject)
            body_tpl = Template(template.body_html)
            ctx = Context(context)
            
            subject = subject_tpl.render(ctx)
            body = body_tpl.render(ctx)
        except Exception as e:
            logger.error(f"Error rendering email template '{template_code}': {e}")
            return False

        # Create Log
        log = EmailLog.objects.create(
            recipient=",".join(recipients),
            subject=subject,
            body=body,
            template=template,
            status='pending'
        )

        # Handle Scheduling
        if schedule_time:
            log.status = 'scheduled'
            log.scheduled_at = schedule_time
            log.save()
            logger.info(f"Email scheduled for {schedule_time} to {recipients}")
            return True

        # Send Immediately
        return EmailService._send_from_log(log, attachments=attachments)

    @staticmethod
    def _send_from_log(log, attachments=None) -> bool:
        """
        Internal method to send an email based on an existing EmailLog.
        """
        try:
            from modules.system_config.helpers import get_system_param
            from django.core.mail import get_connection, EmailMultiAlternatives
            from django.core.mail.backends.smtp import EmailBackend
            
            # Fetch settings
            host = get_system_param('EMAIL_HOST', getattr(settings, 'EMAIL_HOST', ''))
            port_str = get_system_param('EMAIL_PORT', getattr(settings, 'EMAIL_PORT', 587))
            username = get_system_param('EMAIL_HOST_USER', getattr(settings, 'EMAIL_HOST_USER', ''))
            password = get_system_param('EMAIL_HOST_PASSWORD', getattr(settings, 'EMAIL_HOST_PASSWORD', ''))
            use_tls_val = get_system_param('EMAIL_USE_TLS', getattr(settings, 'EMAIL_USE_TLS', 'True'))
            from_email = get_system_param('DEFAULT_FROM_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'))

            # Parse types
            port = int(port_str) if port_str else 587
            use_tls = str(use_tls_val).lower() == 'true'

            # Create Backend Connection
            # If SMTP host is configured in system params, force SMTP backend
            # Otherwise, use the default backend configured in settings.py (e.g., Console for dev)
            if host:
                connection = EmailBackend(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    use_tls=use_tls,
                    fail_silently=False
                )
            else:
                # Fallback to default connection (respects EMAIL_BACKEND setting)
                connection = get_connection(fail_silently=False)
            
            # Send
            recipients = log.recipient.split(",")
            msg = EmailMultiAlternatives(
                subject=log.subject,
                body="", # Plain text fallback
                from_email=from_email,
                to=recipients,
                connection=connection,
            )
            msg.attach_alternative(log.body, "text/html")
            
            if attachments:
                for filename, content, mimetype in attachments:
                    msg.attach(filename, content, mimetype)
            
            msg.send(fail_silently=False)
            
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            logger.info(f"Email sent successfully to {recipients} via {connection.__class__.__name__}")
            return True
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            logger.error(f"Failed to send email: {e}")
            return False

class LineService:
    @staticmethod
    def send_message(template_code: str, line_user_id: str, context: dict) -> bool:
        """
        Sends a Line message (Text or Flex) using a database template.
        """
        try:
            template = LineMessageTemplate.objects.get(code=template_code, is_active=True)
        except LineMessageTemplate.DoesNotExist:
            logger.error(f"Line template '{template_code}' not found or inactive.")
            return False

        # Create Log
        log = LineMessageLog.objects.create(
            recipient_line_id=line_user_id,
            template=template,
            status='pending'
        )

        try:
            from modules.system_config.helpers import get_system_param
            from linebot import LineBotApi
            from linebot.models import TextSendMessage, FlexSendMessage
            from linebot.exceptions import LineBotApiError
            import json

            # Fetch settings
            channel_access_token = get_system_param('LINE_CHANNEL_ACCESS_TOKEN')
            if not channel_access_token:
                raise ValueError("LINE_CHANNEL_ACCESS_TOKEN not configured")

            line_bot_api = LineBotApi(channel_access_token)

            # Prepare Message
            if template.message_type == 'text':
                content_tpl = Template(template.text_content)
                content = content_tpl.render(Context(context))
                message = TextSendMessage(text=content)
            
            elif template.message_type == 'flex':
                # Render JSON string first to replace variables
                json_tpl = Template(template.flex_content_json)
                json_str = json_tpl.render(Context(context))

                try:
                    flex_content = json.loads(json_str)
                    
                    message = FlexSendMessage(
                        alt_text=f"Notification",
                        contents=flex_content
                    )
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid Flex JSON: {e}")
            else:
                raise ValueError(f"Unsupported message type: {template.message_type}")

            # Send
            line_bot_api.push_message(line_user_id, message)

            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            logger.info(f"Line message sent to {line_user_id}")
            return True

        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            logger.error(f"Failed to send Line message: {e}")
            return False
