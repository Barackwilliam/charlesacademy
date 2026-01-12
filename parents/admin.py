from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Parent

User = get_user_model()


class ParentInline(admin.StackedInline):
    model = Parent
    can_delete = False
    verbose_name_plural = 'Parent Profile'
    fk_name = 'user'
    filter_horizontal = ('students',)
    fields = ('full_name', 'phone', 'email', 'relationship', 'students', 'is_active')


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ParentInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_parent_status')
    list_select_related = ('parent_profile',)
    
    def get_parent_status(self, instance):
        if hasattr(instance, 'parent_profile'):
            return "✅ Parent"
        return "❌ Not Parent"
    get_parent_status.short_description = 'Parent Status'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


# Unregister default User admin and register with Parent inline
if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'relationship', 'phone', 'email', 'children_count_display', 'is_active_display', 'created_at')
    list_filter = ('relationship', 'is_active', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'students__full_name', 'students__registration_number')
    filter_horizontal = ('students',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'full_name', 'phone', 'email', 'relationship', 'occupation', 'profile_picture')
        }),
        ('Address Information', {
            'fields': ('address',)
        }),
        ('Children Information', {
            'fields': ('students',)
        }),
        ('Status Information', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def children_count_display(self, obj):
        count = obj.children_count
        color = 'green' if count > 0 else 'red'
        return format_html(f'<span style="color: {color}; font-weight: bold;">{count} Children</span>')
    children_count_display.short_description = 'Children'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✅ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">❌ Inactive</span>')
    is_active_display.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        # Auto-create username if not set
        if not obj.user.username:
            # Create username from phone number
            username = f"parent_{obj.phone.replace('+', '').replace(' ', '')}"
            if User.objects.filter(username=username).exists():
                username = f"{username}_{obj.id}"
            obj.user.username = username
            obj.user.save()
        super().save_model(request, obj, form, change)