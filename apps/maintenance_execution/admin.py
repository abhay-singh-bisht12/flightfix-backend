"""
Django Admin configuration for Maintenance Execution & Documentation module.
"""

from django.contrib import admin
from apps.maintenance_execution.models import (
    MaintenanceExecution,
    MaintenanceDocumentation,
)


class MaintenanceDocumentationInline(admin.TabularInline):
    model = MaintenanceDocumentation
    extra = 0
    fields = ('document_number', 'document_type', 'title', 'sign_off_status', 'signed_off_by', 'signed_off_at')
    readonly_fields = ('created_at',)


@admin.register(MaintenanceExecution)
class MaintenanceExecutionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'work_order',
        'aircraft',
        'executed_by',
        'status',
        'actual_labor_hours',
        'started_at',
        'completed_at',
        'created_at',
    )
    list_filter = (
        'status',
        'started_at',
        'completed_at',
    )
    search_fields = (
        'work_order__work_order_number',
        'aircraft__registration_number',
        'aircraft__model',
        'executed_by__username',
        'executed_by__email',
        'work_performed',
        'findings',
        'corrective_actions',
    )
    ordering = ('-created_at',)
    readonly_fields = ('aircraft', 'created_by', 'created_at', 'updated_at')
    inlines = [MaintenanceDocumentationInline]

    fieldsets = (
        ('Execution Context', {
            'fields': (
                'work_order',
                'maintenance_task',
                'aircraft',
                'executed_by',
                'created_by',
                'status',
            )
        }),
        ('Time & Labor Tracking', {
            'fields': (
                'started_at',
                'completed_at',
                'actual_labor_hours',
            )
        }),
        ('Technical Documentation & Observations', {
            'fields': (
                'work_performed',
                'findings',
                'corrective_actions',
                'remarks',
            )
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MaintenanceDocumentation)
class MaintenanceDocumentationAdmin(admin.ModelAdmin):
    list_display = (
        'document_number',
        'title',
        'execution',
        'document_type',
        'sign_off_status',
        'signed_off_by',
        'signed_off_at',
        'created_at',
    )
    list_filter = (
        'document_type',
        'sign_off_status',
        'signed_off_at',
    )
    search_fields = (
        'document_number',
        'title',
        'issuing_authority',
        'document_reference',
        'remarks',
        'execution__work_order__work_order_number',
        'signed_off_by__username',
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Document Details', {
            'fields': (
                'execution',
                'document_type',
                'document_number',
                'title',
                'issuing_authority',
                'document_reference',
            )
        }),
        ('Certification & Sign-Off', {
            'fields': (
                'sign_off_status',
                'signed_off_by',
                'signed_off_at',
                'remarks',
            )
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
