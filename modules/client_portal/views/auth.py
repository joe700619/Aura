from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.urls import reverse_lazy

from modules.client_portal.forms import ClientPasswordResetForm


class PortalLoginView(LoginView):
    template_name = 'client_portal/auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'EXTERNAL':
            return reverse_lazy('client_portal:dashboard')
        return reverse_lazy('dashboard')


class ClientPasswordResetView(View):
    template_name = 'client_portal/auth/password_reset.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ClientPasswordResetForm()})

    def post(self, request):
        form = ClientPasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request, use_https=request.is_secure())
            return redirect('client_portal:password_reset_done')
        return render(request, self.template_name, {'form': form})


class ClientPasswordResetDoneView(TemplateView):
    template_name = 'client_portal/auth/password_reset_done.html'


class ClientPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'client_portal/auth/password_reset_confirm.html'
    token_generator = default_token_generator
    success_url = reverse_lazy('client_portal:password_reset_complete')
    post_reset_login = False


class ClientPasswordResetCompleteView(TemplateView):
    template_name = 'client_portal/auth/password_reset_complete.html'
