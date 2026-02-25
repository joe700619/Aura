from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from ..models import Account
from ..forms import AccountForm

class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'account_list/account_list.html'
    context_object_name = 'accounts'
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '會計科目管理'
        context['model_name'] = 'internal_accounting:account'
        context['model_app_label'] = 'internal_accounting'
        context['create_button_label'] = '新增科目'
        return context

class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'account_list/account_form.html'
    success_url = reverse_lazy('internal_accounting:account_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增會計科目'
        return context

class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'account_list/account_form.html'
    success_url = reverse_lazy('internal_accounting:account_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯會計科目: {self.object.name}'
        return context

class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = Account
    template_name = 'account_list/account_confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:account_list')
