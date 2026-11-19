"""
Django Admin configuration for ERP & Supply Chain Integration module.
"""

from django.contrib import admin
from apps.supply_chain.models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    fields = ('spare_part', 'quantity_ordered', 'quantity_received', 'unit_price', 'notes')
    readonly_fields = ('created_at',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'supplier_code',
        'name',
        'supplier_type',
        'status',
        'contact_person',
        'email',
        'phone',
        'country',
        'updated_at',
    )
    list_filter = (
        'status',
        'supplier_type',
        'country',
    )
    search_fields = (
        'supplier_code',
        'name',
        'contact_person',
        'email',
        'city',
        'country',
    )
    ordering = ('supplier_code',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Supplier Information', {
            'fields': (
                'supplier_code',
                'name',
                'supplier_type',
                'status',
            )
        }),
        ('Contact Details', {
            'fields': (
                'contact_person',
                'email',
                'phone',
                'address',
                'city',
                'country',
            )
        }),
        ('Notes & Timestamps', {
            'fields': (
                'notes',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        'po_number',
        'supplier',
        'status',
        'priority',
        'order_date',
        'expected_delivery_date',
        'actual_delivery_date',
        'created_by',
        'approved_by',
    )
    list_filter = (
        'status',
        'priority',
        'order_date',
        'expected_delivery_date',
    )
    search_fields = (
        'po_number',
        'supplier__supplier_code',
        'supplier__name',
        'notes',
    )
    ordering = ('-order_date', '-created_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PurchaseOrderItemInline]

    fieldsets = (
        ('Order Identification', {
            'fields': (
                'po_number',
                'supplier',
                'status',
                'priority',
            )
        }),
        ('Schedule & Delivery', {
            'fields': (
                'order_date',
                'expected_delivery_date',
                'actual_delivery_date',
                'delivery_address',
            )
        }),
        ('Authorization & Notes', {
            'fields': (
                'created_by',
                'approved_by',
                'approved_at',
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


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'purchase_order',
        'spare_part',
        'quantity_ordered',
        'quantity_received',
        'unit_price',
        'created_at',
    )
    list_filter = (
        'purchase_order__status',
    )
    search_fields = (
        'purchase_order__po_number',
        'spare_part__part_number',
        'spare_part__name',
    )
    ordering = ('id',)
    readonly_fields = ('created_at', 'updated_at')
