"""
Django Admin configuration for Airworthiness & Regulatory Compliance module.
"""

from django.contrib import admin
from apps.compliance.models import ComplianceRequirement, ComplianceRecord


class ComplianceRecordInline(admin.TabularInline):
    model = ComplianceRecord
    extra = 0
    fields = ('verification_status', 'evidence_reference', 'verified_by', 'verified_at', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(ComplianceRequirement)
class ComplianceRequirementAdmin(admin.ModelAdmin):
    list_display = (
        'requirement_code',
        'title',
        'regulation_type',
        'aircraft',
        'issuing_authority',
        'status',
        'priority',
        'due_date',
        'assigned_to',
        'updated_at',
    )
    list_filter = (
        'status',
        'priority',
        'regulation_type',
        'due_date',
        'issuing_authority',
    )
    search_fields = (
        'requirement_code',
        'title',
        'description',
        'issuing_authority',
        'aircraft__registration_number',
        'aircraft__model',
        'assigned_to__username',
    )
    ordering = ('-due_date',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ComplianceRecordInline]

    fieldsets = (
        ('Requirement Identification', {
            'fields': (
                'requirement_code',
                'title',
                'description',
                'regulation_type',
                'issuing_authority',
            )
        }),
        ('Scope & Aircraft', {
            'fields': (
                'aircraft',
                'priority',
                'status',
                'assigned_to',
                'created_by',
            )
        }),
        ('Regulatory Deadlines', {
            'fields': (
                'effective_date',
                'due_date',
                'notes',
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


@admin.register(ComplianceRecord)
class ComplianceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'requirement',
        'aircraft',
        'verification_status',
        'verified_by',
        'verified_at',
        'evidence_reference',
        'created_at',
    )
    list_filter = (
        'verification_status',
        'verified_at',
    )
    search_fields = (
        'requirement__requirement_code',
        'requirement__title',
        'aircraft__registration_number',
        'evidence_reference',
        'findings',
        'corrective_action',
        'verified_by__username',
    )
    ordering = ('-created_at',)
    readonly_fields = ('aircraft', 'created_at', 'updated_at')

    fieldsets = (
        ('Verification Target', {
            'fields': (
                'requirement',
                'aircraft',
                'maintenance_execution',
            )
        }),
        ('Verification Evidence & Status', {
            'fields': (
                'verification_status',
                'evidence_reference',
                'verified_by',
                'verified_at',
            )
        }),
        ('Observations & Corrective Actions', {
            'fields': (
                'findings',
                'corrective_action',
                'remarks',
            )
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
