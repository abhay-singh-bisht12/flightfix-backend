"""
Serializers for FlightFix Spare Parts Inventory module.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.inventory.models import (
    SparePart,
    InventoryTransaction,
    StockStatus,
    PartCategory,
    TransactionType,
)


class InventoryTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory transaction records (receipts, issues, adjustments, returns).
    """
    spare_part_number = serializers.CharField(
        source='spare_part.part_number',
        read_only=True
    )
    spare_part_name = serializers.CharField(
        source='spare_part.name',
        read_only=True
    )
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    performed_by_username = serializers.CharField(
        source='performed_by.username',
        read_only=True
    )

    class Meta:
        model = InventoryTransaction
        fields = (
            'id',
            'spare_part',
            'spare_part_number',
            'spare_part_name',
            'transaction_type',
            'transaction_type_display',
            'quantity',
            'reference',
            'performed_by',
            'performed_by_username',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'performed_by', 'created_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On update (PUT/PATCH), make core audit fields read-only
        if self.instance is not None:
            self.fields['spare_part'].read_only = True
            self.fields['transaction_type'].read_only = True
            self.fields['quantity'].read_only = True

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Transaction quantity must be greater than zero.")
        return value

    def validate(self, attrs):
        # Only validate stock on new transaction creation
        if not self.instance:
            spare_part = attrs.get('spare_part')
            transaction_type = attrs.get('transaction_type')
            quantity = attrs.get('quantity')

            if transaction_type == TransactionType.ISSUE and spare_part and quantity:
                if spare_part.quantity_in_stock < quantity:
                    raise serializers.ValidationError({
                        'quantity': f"Cannot issue {quantity} unit(s). Current stock is {spare_part.quantity_in_stock}."
                    })

        return attrs


class SparePartSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and creating Spare Parts.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )

    class Meta:
        model = SparePart
        fields = (
            'id',
            'part_number',
            'name',
            'description',
            'category',
            'category_display',
            'manufacturer',
            'manufacturer_part_number',
            'quantity_in_stock',
            'minimum_stock_level',
            'unit_price',
            'location',
            'supplier',
            'status',
            'status_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_part_number(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Part number cannot be blank.")
        qs = SparePart.objects.filter(part_number__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A spare part with this part number already exists.")
        return cleaned

    def validate_quantity_in_stock(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Quantity in stock cannot be negative.")
        return value

    def validate_minimum_stock_level(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Minimum stock level cannot be negative.")
        return value

    def validate_unit_price(self, value):
        if value is not None and value < Decimal('0.00'):
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value


class SparePartDetailSerializer(SparePartSerializer):
    """
    Detailed serializer for a single Spare Part including recent transaction history.
    """
    recent_transactions = serializers.SerializerMethodField()

    class Meta(SparePartSerializer.Meta):
        fields = SparePartSerializer.Meta.fields + ('recent_transactions',)

    def get_recent_transactions(self, obj):
        # Fetch the 10 most recent transactions for this part
        transactions = obj.transactions.select_related('performed_by').all()[:10]
        return InventoryTransactionSerializer(transactions, many=True).data
