"""
Views and ViewSets for FlightFix Spare Parts Inventory module.
"""

from django.db import models
from rest_framework import viewsets, filters

from apps.aircraft.pagination import StandardResultsSetPagination
from apps.inventory.models import (
    SparePart,
    InventoryTransaction,
    StockStatus,
)
from apps.inventory.permissions import InventoryPermission
from apps.inventory.serializers import (
    SparePartSerializer,
    SparePartDetailSerializer,
    InventoryTransactionSerializer,
)


class SparePartViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Spare Parts.
    Supports search, multi-field filtering, ordering, and pagination.
    """
    queryset = SparePart.objects.all()
    permission_classes = [InventoryPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'part_number',
        'name',
        'description',
        'manufacturer',
        'manufacturer_part_number',
        'category',
        'location',
        'supplier',
    ]

    ordering_fields = [
        'part_number',
        'name',
        'quantity_in_stock',
        'minimum_stock_level',
        'unit_price',
        'status',
        'category',
        'created_at',
    ]
    ordering = ['part_number']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SparePartDetailSerializer
        return SparePartSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        # Filter by category
        category_param = self.request.query_params.get('category')
        if category_param:
            queryset = queryset.filter(category__iexact=category_param.strip())

        # Filter by manufacturer
        manufacturer_param = self.request.query_params.get('manufacturer')
        if manufacturer_param:
            queryset = queryset.filter(manufacturer__icontains=manufacturer_param.strip())

        # Filter by supplier
        supplier_param = self.request.query_params.get('supplier')
        if supplier_param:
            queryset = queryset.filter(supplier__icontains=supplier_param.strip())

        # Filter by location
        location_param = self.request.query_params.get('location')
        if location_param:
            queryset = queryset.filter(location__icontains=location_param.strip())

        # Filter low stock
        low_stock_param = self.request.query_params.get('low_stock')
        if low_stock_param is not None and low_stock_param.lower() in ('true', '1', 'yes'):
            queryset = queryset.filter(
                models.Q(status=StockStatus.LOW_STOCK) |
                models.Q(quantity_in_stock__lte=models.F('minimum_stock_level'))
            )

        return queryset


class InventoryTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Inventory Transactions.
    Supports tracking receipts, issues, adjustments, and returns with search and filtering.
    """
    queryset = InventoryTransaction.objects.select_related(
        'spare_part',
        'performed_by'
    ).all()
    permission_classes = [InventoryPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'reference',
        'notes',
        'spare_part__part_number',
        'spare_part__name',
        'performed_by__username',
    ]

    ordering_fields = [
        'created_at',
        'quantity',
        'transaction_type',
    ]
    ordering = ['-created_at']
    serializer_class = InventoryTransactionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by spare part (ID or part number)
        part_param = self.request.query_params.get('spare_part')
        if part_param:
            if part_param.isdigit():
                queryset = queryset.filter(spare_part_id=part_param)
            else:
                queryset = queryset.filter(spare_part__part_number__iexact=part_param.strip())

        # Filter by transaction type
        type_param = self.request.query_params.get('transaction_type')
        if type_param:
            queryset = queryset.filter(transaction_type__iexact=type_param.strip())

        # Filter by performed_by (ID or username)
        user_param = self.request.query_params.get('performed_by')
        if user_param:
            if user_param.isdigit():
                queryset = queryset.filter(performed_by_id=user_param)
            else:
                queryset = queryset.filter(performed_by__username__iexact=user_param.strip())

        # Filter by date range
        start_date = self.request.query_params.get('date_from') or self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date.strip())

        end_date = self.request.query_params.get('date_to') or self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date.strip())

        return queryset

    def perform_create(self, serializer):
        # Automatically assign the authenticated user to performed_by
        serializer.save(performed_by=self.request.user)
