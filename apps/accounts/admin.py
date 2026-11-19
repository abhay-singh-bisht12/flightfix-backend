"""
Admin interface registration for FlightFix User model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom Admin configuration for FlightFix RBAC User model.
    """
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'phone',
        'is_active',
        'is_staff',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Role & Permissions', {
            'fields': (
                'role',
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'password',
                'first_name',
                'last_name',
                'phone',
                'role',
                'is_active',
                'is_staff',
            ),
        }),
    )
