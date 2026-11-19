"""
Django Admin configuration for Spare Parts Inventory module.
"""

from django.contrib import admin
from apps.inventory.models import SparePart, InventoryTransaction


class InventoryTransactionInline(admin.TabularInline):
    model = InventoryTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'quantity', 'reference', 'performed_by', 'created_at', 'notes')
    can_delete = False
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = (
        'part_number',
        'name',
        'category',
        'quantity_in_stock',
        'minimum_stock_level',
        'status',
        'unit_price',
        'location',
        'manufacturer',
        'supplier',
        'updated_at',
    )
    list_filter = (
        'status',
        'category',
        'manufacturer',
        'supplier',
    )
    search_fields = (
        'part_number',
        'name',
        'description',
        'manufacturer',
        'manufacturer_part_number',
        'location',
        'supplier',
    )
    ordering = ('part_number',)
    readonly_fields = ('status', 'created_at', 'updated_at')
    inlines = [InventoryTransactionInline]

    fieldsets = (
        ('Part Identification', {
            'fields': (
                'part_number',
                'name',
                'category',
                'description',
                'manufacturer',
                'manufacturer_part_number',
            )
        }),
        ('Stock & Inventory Levels', {
            'fields': (
                'quantity_in_stock',
                'minimum_stock_level',
                'status',
                'unit_price',
            )
        }),
        ('Storage & Procurement', {
            'fields': (
                'location',
                'supplier',
            )
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'spare_part',
        'transaction_type',
        'quantity',
        'reference',
        'performed_by',
        'created_at',
    )
    list_filter = (
        'transaction_type',
        'created_at',
    )
    search_fields = (
        'reference',
        'notes',
        'spare_part__part_number',
        'spare_part__name',
        'performed_by__username',
        'performed_by__email',
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'spare_part',
                'transaction_type',
                'quantity',
                'reference',
                'performed_by',
            )
        }),
        ('Audit & Notes', {
            'fields': (
                'notes',
                'created_at',
            )
        }),
    )
