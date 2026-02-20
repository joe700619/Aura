from django.contrib import admin
from .models import MenuItem

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'parent', 'is_active')
    list_filter = ('parent', 'is_active', 'roles')
    search_fields = ('title', 'url_name')
    ordering = ('order',)
    filter_horizontal = ('roles',)

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
