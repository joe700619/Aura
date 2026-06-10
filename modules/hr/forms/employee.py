from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Employee


# 可檢視完整身分證字號的群組（其他能進 HR 模組的群組只能看到遮罩）
ID_NUMBER_FULL_ACCESS_GROUPS = ['人資組', 'Admin']


def can_view_full_id_number(user):
    """檢查使用者是否可檢視完整身分證字號（人資組、Admin 或 superuser）"""
    if user is None or not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name__in=ID_NUMBER_FULL_ACCESS_GROUPS).exists()


class EmployeeForm(forms.ModelForm):
    """
    員工表單

    表單分為三個區塊：
    - 區塊一：基本資料
    - 區塊二：通訊方式
    - 區塊三：在職狀態

    身分證字號為敏感資料：
    - 編輯模式下，僅人資組 / Admin / superuser 看得到此欄位，
      其他人會被移除欄位（template 改顯示遮罩值，存檔不影響原值）
    - 新增模式下保留欄位：值由填寫者自行輸入，不涉及揭露既有資料
    """

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_view_full_id_number = can_view_full_id_number(user)
        if self.instance.pk and not self.can_view_full_id_number:
            # 沒權限的人連 HTML 原始碼都不該收到完整身分證，直接移除欄位
            del self.fields['id_number']

    class Meta:
        model = Employee
        fields = [
            # 區塊一：基本資料
            'user',
            'name',
            'gender',
            'id_number',
            'line_id',
            'extension',
            # 區塊二：通訊方式
            'phone',
            'address',
            'email',
            # 區塊三：在職狀態
            'employment_status',
            'hire_date',
            'resignation_date',
            'team',
            'supervisor',
        ]
        widgets = {
            'user': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入員工姓名'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            # PasswordInput(render_value=True)：有權限者預設也以遮罩顯示，
            # 點 template 的「顯示」按鈕（Alpine :type 切換）才看得到明碼，防旁人窺視
            'id_number': forms.PasswordInput(render_value=True, attrs={
                'class': 'w-full px-3 py-2 pr-12 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：A123456789',
                'maxlength': '10',
                'autocomplete': 'off',
                ':type': "show ? 'text' : 'password'",
            }),
            'line_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入 Line ID'
            }),
            'extension': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：101'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：02-12345678'
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入地址'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：employee@example.com'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            'resignation_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            'team': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'supervisor': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
        }


