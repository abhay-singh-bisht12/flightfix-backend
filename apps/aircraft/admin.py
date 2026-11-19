"""
Django Admin configuration for Aircraft and Equipment models.
"""

from django.contrib import admin
from apps.aircraft.models import Aircraft, Equipment


class EquipmentInline(admin.TabularInline):
    model = Equipment
    extra = 0
    fields = ('equipment_code', 'name', 'equipment_type', 'status', 'location')
    readonly_fields = ('equipment_code', 'name', 'equipment_type')
    show_change_link = True


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    """
    Admin configuration for Aircraft fleet tracking.
    """
    list_display = (
        'id',
        'registration_number',
        'model',
        'aircraft_type',
        'manufacturer',
        'serial_number',
        'status',
        'manufacture_date',
        'service_entry_date',
        'created_at',
    )
    list_filter = ('status', 'aircraft_type', 'manufacturer')
    search_fields = (
        'registration_number',
        'model',
        'serial_number',
        'manufacturer',
        'aircraft_type',
    )
    ordering = ('-created_at',)
    inlines = [EquipmentInline]
    fieldsets = (
        ('Aircraft Identity', {
            'fields': (
                'registration_number',
                'model',
                'aircraft_type',
                'manufacturer',
                'serial_number',
            )
        }),
        ('Operational Status', {
            'fields': ('status',)
        }),
        ('Lifecycle Dates', {
            'fields': ('manufacture_date', 'service_entry_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Equipment and components.
    """
    list_display = (
        'id',
        'equipment_code',
        'name',
        'equipment_type',
        'manufacturer',
        'serial_number',
        'status',
        'aircraft',
        'location',
        'created_at',
    )
    list_filter = ('status', 'equipment_type', 'manufacturer')
    search_fields = (
        'equipment_code',
        'name',
        'serial_number',
        'manufacturer',
        'location',
    )
    ordering = ('-created_at',)
    fieldsets = (
        ('Equipment Identity', {
            'fields': (
                'equipment_code',
                'name',
                'equipment_type',
                'manufacturer',
                'serial_number',
            )
        }),
        ('Status & Assignment', {
            'fields': ('status', 'aircraft', 'location')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
