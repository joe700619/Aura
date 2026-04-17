from django.contrib import admin
from .models import MenuItem

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'parent', 'url_name', 'required_permission', 'is_active')
    list_filter = ('parent', 'is_active')
    search_fields = ('title', 'url_name', 'required_permission')
    ordering = ('order',)
    fieldsets = (
        (None, {
            'fields': ('title', 'parent', 'order', 'is_active')
        }),
        ('連結設定', {
            'fields': ('url_name', 'icon_svg')
        }),
        ('權限設定', {
            'fields': ('required_permission',),
            'description': '格式：app_label.codename（例如 hr.view_employee）。留空表示所有登入者皆可看到。',
        }),
    )

from .models import SystemParameter

@admin.register(SystemParameter)
class SystemParameterAdmin(admin.ModelAdmin):
    list_display = ('key', 'value_preview', 'group', 'description', 'updated_at')
    list_filter = ('group', 'is_secret')
    search_fields = ('key', 'description')
    
    def value_preview(self, obj):
        if obj.is_secret:
            return "********"
        return obj.value
    value_preview.short_description = "參數值"
