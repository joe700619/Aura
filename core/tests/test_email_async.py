"""
驗證批次 4 的 celery 寄信非同步機制（測試環境用 EAGER mode）。
"""
import pytest


@pytest.mark.django_db
class TestSendEmailAsync:

    def test_send_email_async_succeeds(self, settings):
        from core.tasks import send_email_async
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        result = send_email_async.delay(
            subject='測試',
            body_html='<p>hi</p>',
            recipients=['to@example.com'],
        )
        # EAGER mode 下，呼叫立即回傳結果
        assert result.successful()
        assert result.result['sent'] is True
        assert result.result['recipients'] == 1

    def test_send_email_async_with_attachment(self, settings):
        import base64
        from core.tasks import send_email_async
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        result = send_email_async.delay(
            subject='含附件',
            body_html='<p>see attachment</p>',
            recipients=['to@example.com'],
            attachments_b64=[{
                'filename': 'test.txt',
                'content_b64': base64.b64encode(b'hello').decode('ascii'),
                'mimetype': 'text/plain',
            }],
        )
        assert result.successful()

    def test_send_email_async_no_recipients_returns_falsy(self, settings):
        from core.tasks import send_email_async
        result = send_email_async.delay('subj', 'body', recipients=[])
        assert result.result['sent'] is False


@pytest.mark.django_db
class TestEmailServiceAsync:

    def test_send_email_creates_log_and_dispatches(self, settings):
        """EmailService.send_email 應建立 EmailLog 並派出 task"""
        from core.notifications.models import EmailTemplate, EmailLog
        from core.notifications.services import EmailService
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        EmailTemplate.objects.create(
            code='_test_unit',
            name='unit test',
            subject='Hello {{ name }}',
            body_html='<p>{{ name }}</p>',
            is_active=True,
        )

        before = EmailLog.objects.count()
        ok = EmailService.send_email('_test_unit', ['x@example.com'], {'name': 'Alice'})

        assert ok is True
        assert EmailLog.objects.count() == before + 1
        log = EmailLog.objects.latest('id')
        assert 'Alice' in log.subject
        # EAGER 模式下 task 已執行完成，狀態應為 sent
        assert log.status == 'sent'

    def test_template_not_found_returns_false(self):
        from core.notifications.services import EmailService
        ok = EmailService.send_email('NONEXISTENT', ['x@example.com'], {})
        assert ok is False
