from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template import loader
from django.core.mail import EmailMultiAlternatives, get_connection
from django.conf import settings as django_settings

from modules.bookkeeping.models import BookkeepingClient

_INPUT = 'portal-input'


class ClientSettingsForm(forms.ModelForm):
    class Meta:
        model = BookkeepingClient
        fields = [
            'tax_registration_no',
            'contact_person', 'phone', 'mobile', 'email',
            'correspondence_address', 'registered_address',
            'national_tax_password', 'e_invoice_account', 'e_invoice_password',
            'has_group_invoice',
        ]
        widgets = {
            'tax_registration_no': forms.TextInput(attrs={'class': _INPUT}),
            'contact_person': forms.TextInput(attrs={'class': _INPUT}),
            'phone': forms.TextInput(attrs={'class': _INPUT}),
            'mobile': forms.TextInput(attrs={'class': _INPUT}),
            'email': forms.EmailInput(attrs={'class': _INPUT}),
            'correspondence_address': forms.TextInput(attrs={'class': _INPUT}),
            'registered_address': forms.TextInput(attrs={'class': _INPUT}),
            'national_tax_password': forms.TextInput(attrs={'class': _INPUT, 'autocomplete': 'off'}),
            'e_invoice_account': forms.TextInput(attrs={'class': _INPUT, 'autocomplete': 'off'}),
            'e_invoice_password': forms.TextInput(attrs={'class': _INPUT, 'autocomplete': 'off'}),
        }


class ClientPasswordResetForm(forms.Form):
    username = forms.CharField(
        label='統一編號',
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '請輸入公司統一編號', 'autofocus': True,
                                      'class': _INPUT}),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': '請輸入帳戶綁定的 Email',
                                       'class': _INPUT}),
    )

    def clean(self):
        data = super().clean()
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        self._user = None
        if username and email:
            User = get_user_model()
            try:
                self._user = User.objects.get(
                    username=username,
                    email__iexact=email,
                    is_active=True,
                    role='EXTERNAL',
                )
            except User.DoesNotExist:
                pass
        return data

    def save(self, request, use_https=False):
        user = getattr(self, '_user', None)
        if not user:
            return

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        from django.contrib.sites.shortcuts import get_current_site
        current_site = get_current_site(request)

        context = {
            'user': user,
            'domain': current_site.domain,
            'uid': uid,
            'token': token,
            'protocol': 'https' if use_https else 'http',
        }

        subject = loader.render_to_string('client_portal/auth/password_reset_subject.txt', context)
        subject = ''.join(subject.splitlines())
        body_html = loader.render_to_string('client_portal/auth/password_reset_email.html', context)

        from modules.system_config.helpers import get_system_param
        from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

        host = get_system_param('EMAIL_HOST', '')
        from_email = get_system_param('DEFAULT_FROM_EMAIL', django_settings.DEFAULT_FROM_EMAIL)

        if host:
            port = int(get_system_param('EMAIL_PORT', 587))
            smtp_user = get_system_param('EMAIL_HOST_USER', '')
            smtp_pass = get_system_param('EMAIL_HOST_PASSWORD', '')
            use_tls = str(get_system_param('EMAIL_USE_TLS', 'True')).lower() == 'true'
            connection = SMTPBackend(
                host=host, port=port,
                username=smtp_user, password=smtp_pass,
                use_tls=use_tls, fail_silently=False,
            )
        else:
            connection = get_connection(fail_silently=False)

        msg = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[user.email],
            connection=connection,
        )
        msg.attach_alternative(body_html, 'text/html')
        msg.send()
