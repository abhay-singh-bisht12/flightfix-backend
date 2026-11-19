"""
Django Admin interface for Maintenance Planning & Scheduling.
"""

from django.contrib import admin
from apps.maintenance_planning.models import MaintenanceSchedule, MaintenanceTask


class MaintenanceTaskInline(admin.TabularInline):
    model = MaintenanceTask
    extra = 1
    fields = ('task_order', 'task_name', 'status', 'estimated_hours', 'completed_at')
    ordering = ('task_order',)


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'aircraft',
        'maintenance_type',
        'priority',
        'status',
        'planned_date',
        'due_date',
        'assigned_to',
        'created_by',
        'created_at',
    )
    list_filter = (
        'status',
        'priority',
        'maintenance_type',
        'planned_date',
        'due_date',
    )
    search_fields = (
        'title',
        'description',
        'aircraft__registration_number',
        'aircraft__model',
        'assigned_to__username',
        'assigned_to__email',
    )
    ordering = ('-created_at',)
    inlines = [MaintenanceTaskInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Schedule Information', {
            'fields': (
                'title',
                'aircraft',
                'description',
                'maintenance_type',
                'priority',
                'status',
            )
        }),
        ('Timeline', {
            'fields': ('planned_date', 'due_date')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Additional Notes', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'task_order',
        'task_name',
        'schedule',
        'status',
        'estimated_hours',
        'completed_at',
        'created_at',
    )
    list_filter = ('status', 'schedule__maintenance_type', 'schedule__priority')
    search_fields = (
        'task_name',
        'description',
        'schedule__title',
        'schedule__aircraft__registration_number',
    )
    ordering = ('schedule', 'task_order', 'id')
    readonly_fields = ('created_at', 'updated_at')
