"""
Django Admin interface for Work Order Management.
"""

from django.contrib import admin
from apps.work_orders.models import WorkOrder


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        'work_order_number',
        'title',
        'aircraft',
        'work_order_type',
        'priority',
        'status',
        'assigned_to',
        'planned_start_date',
        'planned_completion_date',
        'created_by',
        'created_at',
    )
    list_filter = (
        'status',
        'priority',
        'work_order_type',
        'planned_start_date',
        'planned_completion_date',
    )
    search_fields = (
        'work_order_number',
        'title',
        'description',
        'findings',
        'corrective_action',
        'aircraft__registration_number',
        'aircraft__model',
        'assigned_to__username',
        'assigned_to__email',
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Identification & Aircraft', {
            'fields': (
                'work_order_number',
                'title',
                'aircraft',
                'maintenance_schedule',
                'work_order_type',
                'priority',
                'status',
            )
        }),
        ('Scope of Work', {
            'fields': ('description', 'findings', 'corrective_action')
        }),
        ('Schedule & Tracking', {
            'fields': (
                'planned_start_date',
                'planned_completion_date',
                'actual_start_date',
                'actual_completion_date',
                'estimated_hours',
                'actual_hours',
            )
        }),
        ('Assignments & Meta', {
            'fields': (
                'assigned_to',
                'created_by',
                'notes',
                'created_at',
                'updated_at',
            )
        }),
    )
