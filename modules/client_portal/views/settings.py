from django.views import View
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages

from modules.client_portal.mixins import ClientRequiredMixin
from modules.client_portal.forms import ClientSettingsForm
from modules.bookkeeping.models.group_invoice import GroupInvoice


class SettingsView(ClientRequiredMixin, View):
    template_name = 'client_portal/settings.html'

    def _get_client(self):
        return self.request.user.bookkeeping_client_profile

    def _context(self, client, form=None, password_form=None):
        return {
            'client': client,
            'form': form or ClientSettingsForm(instance=client),
            'group_invoices': client.group_invoices.filter(is_deleted=False),
            'password_form': password_form,
            'password_changed': self.request.GET.get('password_changed') == '1',
        }

    def get(self, request):
        client = self._get_client()
        return render(request, self.template_name, self._context(client))

    def post(self, request):
        client = self._get_client()
        section = request.POST.get('section')

        if section == 'change_password':
            return self._handle_password_change(request, client)

        return self._handle_settings_save(request, client)

    def _handle_settings_save(self, request, client):
        form = ClientSettingsForm(request.POST, instance=client)
        if form.is_valid():
            form.save()

            # 統購發票數量
            for key, value in request.POST.items():
                if key.startswith('group_invoice_qty_'):
                    try:
                        invoice_id = int(key.replace('group_invoice_qty_', ''))
                        qty = max(0, int(value))
                        GroupInvoice.objects.filter(pk=invoice_id, client=client).update(quantity=qty)
                    except (ValueError, TypeError):
                        pass

            # 通知方式 / 繳稅方式（直接存到 BookkeepingClient）
            notification_method = request.POST.get('tax_notification_method', '')
            payment_method = request.POST.get('tax_payment_method', '')
            valid_notifications = {'line', 'email', 'both', ''}
            valid_payments = {'self_pay', 'office_pay', 'auto_debit', ''}
            if notification_method in valid_notifications and payment_method in valid_payments:
                client.notification_method = notification_method or None
                client.payment_method = payment_method or None
                client.save(update_fields=['notification_method', 'payment_method'])

            # 勞務報酬繳費提醒開關
            client.service_remuneration_reminder_enabled = (
                request.POST.get('service_remuneration_reminder_enabled') == 'on'
            )
            client.save(update_fields=['service_remuneration_reminder_enabled'])

            messages.success(request, '設定已儲存成功。')
            return redirect('client_portal:settings')

        return render(request, self.template_name, self._context(client, form=form))

    def _handle_password_change(self, request, client):
        from django.contrib.auth.forms import PasswordChangeForm
        from django.contrib.auth import update_session_auth_hash

        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            return redirect(reverse_lazy('client_portal:settings') + '?password_changed=1')

        return render(request, self.template_name, self._context(client, password_form=password_form))
