"""
Serializers for FlightFix ERP & Supply Chain Integration module.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.supply_chain.models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    SupplierStatus,
    PurchaseOrderStatus,
)
from apps.inventory.models import SparePart


class SupplierSerializer(serializers.ModelSerializer):
    """
    Serializer for Suppliers / Vendors.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    supplier_type_display = serializers.CharField(
        source='get_supplier_type_display',
        read_only=True
    )

    class Meta:
        model = Supplier
        fields = (
            'id',
            'supplier_code',
            'name',
            'contact_person',
            'email',
            'phone',
            'address',
            'city',
            'country',
            'status',
            'status_display',
            'supplier_type',
            'supplier_type_display',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_supplier_code(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Supplier code cannot be blank.")
        qs = Supplier.objects.filter(supplier_code__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A supplier with this supplier code already exists.")
        return cleaned


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual Purchase Order Line Items.
    """
    purchase_order_number = serializers.CharField(
        source='purchase_order.po_number',
        read_only=True
    )
    spare_part_number = serializers.CharField(
        source='spare_part.part_number',
        read_only=True
    )
    spare_part_name = serializers.CharField(
        source='spare_part.name',
        read_only=True
    )
    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    quantity_pending = serializers.IntegerField(
        read_only=True
    )

    class Meta:
        model = PurchaseOrderItem
        fields = (
            'id',
            'purchase_order',
            'purchase_order_number',
            'spare_part',
            'spare_part_number',
            'spare_part_name',
            'quantity_ordered',
            'quantity_received',
            'quantity_pending',
            'unit_price',
            'line_total',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'line_total', 'quantity_pending', 'created_at', 'updated_at')

    def validate_quantity_ordered(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Quantity ordered must be greater than zero.")
        return value

    def validate_quantity_received(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Quantity received cannot be negative.")
        return value

    def validate_unit_price(self, value):
        if value is not None and value < Decimal('0.00'):
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value

    def validate(self, attrs):
        po = attrs.get('purchase_order') or (self.instance.purchase_order if self.instance else None)
        part = attrs.get('spare_part') or (self.instance.spare_part if self.instance else None)
        qty_ordered = attrs.get('quantity_ordered') or (self.instance.quantity_ordered if self.instance else None)
        qty_received = attrs.get('quantity_received') if 'quantity_received' in attrs else (self.instance.quantity_received if self.instance else 0)

        if qty_ordered is not None and qty_received is not None and qty_received > qty_ordered:
            raise serializers.ValidationError({
                'quantity_received': "Quantity received cannot exceed quantity ordered."
            })

        # Check duplicate spare part inside the same PO
        if po and part:
            qs = PurchaseOrderItem.objects.filter(purchase_order=po, spare_part=part)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'spare_part': f"Spare part '{part.part_number}' is already added to this purchase order."
                })

        return attrs


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and creating Purchase Orders.
    """
    supplier_code = serializers.CharField(
        source='supplier.supplier_code',
        read_only=True
    )
    supplier_name = serializers.CharField(
        source='supplier.name',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    approved_by_username = serializers.CharField(
        source='approved_by.username',
        read_only=True
    )
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = (
            'id',
            'po_number',
            'supplier',
            'supplier_code',
            'supplier_name',
            'order_date',
            'expected_delivery_date',
            'actual_delivery_date',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'created_by',
            'created_by_username',
            'approved_by',
            'approved_by_username',
            'approved_at',
            'delivery_address',
            'notes',
            'total_amount',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def get_total_amount(self, obj):
        items = obj.items.all()
        return sum(item.line_total for item in items)

    def validate_po_number(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Purchase order number cannot be blank.")
        qs = PurchaseOrder.objects.filter(po_number__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A purchase order with this PO number already exists.")
        return cleaned

    def validate(self, attrs):
        order_date = attrs.get('order_date') or (self.instance.order_date if self.instance else None)
        expected_date = attrs.get('expected_delivery_date') or (self.instance.expected_delivery_date if self.instance else None)
        actual_date = attrs.get('actual_delivery_date') or (self.instance.actual_delivery_date if self.instance else None)
        supplier = attrs.get('supplier') or (self.instance.supplier if self.instance else None)
        status_val = attrs.get('status') or (self.instance.status if self.instance else None)

        # 1. Date chronological sequence
        if order_date and expected_date and expected_date < order_date:
            raise serializers.ValidationError({
                'expected_delivery_date': "Expected delivery date cannot be before order date."
            })

        if order_date and actual_date and actual_date < order_date:
            raise serializers.ValidationError({
                'actual_delivery_date': "Actual delivery date cannot be before order date."
            })

        # 2. Re-activation check on cancelled orders
        if self.instance and self.instance.status == PurchaseOrderStatus.CANCELLED and status_val != PurchaseOrderStatus.CANCELLED:
            raise serializers.ValidationError({
                'status': "Cancelled purchase orders cannot be reopened or reactivated."
            })

        # 3. Active supplier check
        if supplier and supplier.status != SupplierStatus.ACTIVE:
            if not self.instance or status_val == PurchaseOrderStatus.APPROVED:
                raise serializers.ValidationError({
                    'supplier': f"Supplier '{supplier.name}' is {supplier.get_status_display().lower()} and cannot be used for purchase orders."
                })

        # 4. Approval requirements
        if status_val == PurchaseOrderStatus.APPROVED:
            approved_by = attrs.get('approved_by') or (self.instance.approved_by if self.instance else None)
            if not approved_by:
                raise serializers.ValidationError({
                    'approved_by': "Approved purchase orders must specify an approved_by user."
                })

        return attrs


class PurchaseOrderDetailSerializer(PurchaseOrderSerializer):
    """
    Detailed serializer including nested line items.
    """
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta(PurchaseOrderSerializer.Meta):
        fields = PurchaseOrderSerializer.Meta.fields + ('items',)
