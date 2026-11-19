"""
Views and ViewSets for FlightFix ERP & Supply Chain Integration module.
"""

from django.db import models, transaction
from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.aircraft.pagination import StandardResultsSetPagination
from apps.inventory.models import InventoryTransaction, TransactionType
from apps.supply_chain.models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from apps.supply_chain.permissions import (
    SupplyChainPermission,
    CanReceivePOPermission,
)
from apps.supply_chain.serializers import (
    SupplierSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderDetailSerializer,
    PurchaseOrderItemSerializer,
)


class SupplierViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Suppliers / Vendors.
    Supports search, multi-parameter filtering, ordering, and pagination.
    """
    queryset = Supplier.objects.all()
    permission_classes = [SupplyChainPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'supplier_code',
        'name',
        'contact_person',
        'email',
        'city',
        'country',
    ]
    ordering_fields = [
        'supplier_code',
        'name',
        'status',
        'created_at',
    ]
    ordering = ['supplier_code']
    serializer_class = SupplierSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        type_param = self.request.query_params.get('supplier_type')
        if type_param:
            queryset = queryset.filter(supplier_type__iexact=type_param.strip())

        country_param = self.request.query_params.get('country')
        if country_param:
            queryset = queryset.filter(country__icontains=country_param.strip())

        return queryset


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Purchase Orders with receiving workflow and inventory integration.
    """
    queryset = PurchaseOrder.objects.select_related(
        'supplier',
        'created_by',
        'approved_by'
    ).prefetch_related('items__spare_part').all()

    permission_classes = [SupplyChainPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'po_number',
        'supplier__supplier_code',
        'supplier__name',
        'notes',
        'items__spare_part__part_number',
        'items__spare_part__name',
    ]
    ordering_fields = [
        'order_date',
        'expected_delivery_date',
        'actual_delivery_date',
        'priority',
        'status',
        'created_at',
    ]
    ordering = ['-order_date', '-created_at']

    def get_serializer_class(self):
        if self.action in ('retrieve', 'receive'):
            return PurchaseOrderDetailSerializer
        return PurchaseOrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by supplier (ID or code)
        supplier_param = self.request.query_params.get('supplier')
        if supplier_param:
            if supplier_param.isdigit():
                queryset = queryset.filter(supplier_id=supplier_param)
            else:
                queryset = queryset.filter(supplier__supplier_code__iexact=supplier_param.strip())

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        # Filter by priority
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority__iexact=priority_param.strip())

        # Filter by supplier status
        supplier_status_param = self.request.query_params.get('supplier_status')
        if supplier_status_param:
            queryset = queryset.filter(supplier__status__iexact=supplier_status_param.strip())

        # Filter by dates
        order_date_param = self.request.query_params.get('order_date')
        if order_date_param:
            queryset = queryset.filter(order_date=order_date_param.strip())

        expected_date_param = self.request.query_params.get('expected_delivery_date')
        if expected_date_param:
            queryset = queryset.filter(expected_delivery_date=expected_date_param.strip())

        # Filter by spare part ID or part number
        part_param = self.request.query_params.get('spare_part')
        if part_param:
            if part_param.isdigit():
                queryset = queryset.filter(items__spare_part_id=part_param).distinct()
            else:
                queryset = queryset.filter(items__spare_part__part_number__iexact=part_param.strip()).distinct()

        return queryset

    def perform_create(self, serializer):
        approved_by = serializer.validated_data.get('approved_by')
        approved_at = None
        if serializer.validated_data.get('status') == PurchaseOrderStatus.APPROVED:
            if not approved_by:
                approved_by = self.request.user
            approved_at = timezone.now()

        serializer.save(
            created_by=self.request.user,
            approved_by=approved_by,
            approved_at=approved_at
        )

    @action(detail=True, methods=['post'], permission_classes=[CanReceivePOPermission])
    def receive(self, request, pk=None):
        """
        Receives quantities for one or more purchase order items.
        Automatically updates stock in inventory.SparePart and creates InventoryTransaction(type=RECEIPT).
        """
        po = self.get_object()

        # 1. Validate PO status
        valid_receiving_statuses = (
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.ORDERED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        )
        if po.status not in valid_receiving_statuses:
            return Response(
                {
                    "error": f"Cannot receive items on purchase order '{po.po_number}'. "
                             f"Current status is '{po.get_status_display()}'. "
                             "PO must be Approved, Ordered, or Partially Received to accept deliveries."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        items_data = request.data.get('items')
        if not items_data or not isinstance(items_data, list):
            return Response(
                {"error": "A non-empty 'items' list must be provided with receiving details."},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery_notes = request.data.get('notes', f"Received against Purchase Order {po.po_number}")

        # 2. Process receiving atomically
        with transaction.atomic():
            for entry in items_data:
                item_id = entry.get('purchase_order_item') or entry.get('id')
                qty_to_receive = entry.get('quantity_received')

                if not item_id:
                    return Response(
                        {"error": "Each item entry must include 'purchase_order_item'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if qty_to_receive is None or not isinstance(qty_to_receive, int) or qty_to_receive <= 0:
                    return Response(
                        {"error": f"Invalid receiving quantity '{qty_to_receive}'. Must be a positive integer."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Fetch and lock item row
                try:
                    po_item = PurchaseOrderItem.objects.select_for_update().get(
                        pk=item_id,
                        purchase_order=po
                    )
                except PurchaseOrderItem.DoesNotExist:
                    return Response(
                        {"error": f"Purchase order item #{item_id} does not exist in PO '{po.po_number}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Prevent over-receiving
                pending_qty = po_item.quantity_ordered - po_item.quantity_received
                if qty_to_receive > pending_qty:
                    return Response(
                        {
                            "error": f"Cannot receive {qty_to_receive} units for part '{po_item.spare_part.part_number}'. "
                                     f"Only {pending_qty} units are pending on this order."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update item received quantity
                po_item.quantity_received += qty_to_receive
                po_item.save(update_fields=['quantity_received', 'updated_at'])

                # Log inventory transaction (this automatically increments SparePart.quantity_in_stock atomically)
                InventoryTransaction.objects.create(
                    spare_part=po_item.spare_part,
                    transaction_type=TransactionType.RECEIPT,
                    quantity=qty_to_receive,
                    reference=po.po_number,
                    performed_by=request.user,
                    notes=delivery_notes
                )

            # 3. Update overall PO status based on all items
            all_items = list(PurchaseOrderItem.objects.filter(purchase_order=po))
            all_fully_received = all(item.quantity_received >= item.quantity_ordered for item in all_items)
            any_received = any(item.quantity_received > 0 for item in all_items)

            if all_fully_received:
                po.status = PurchaseOrderStatus.RECEIVED
                if not po.actual_delivery_date:
                    po.actual_delivery_date = timezone.now().date()
            elif any_received:
                po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

            po.save(update_fields=['status', 'actual_delivery_date', 'updated_at'])

        # Refresh and return updated PO details
        po.refresh_from_db()
        serializer = PurchaseOrderDetailSerializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for individual Purchase Order Line Items.
    """
    queryset = PurchaseOrderItem.objects.select_related(
        'purchase_order',
        'spare_part'
    ).all()
    permission_classes = [SupplyChainPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'purchase_order__po_number',
        'spare_part__part_number',
        'spare_part__name',
    ]
    ordering_fields = [
        'id',
        'quantity_ordered',
        'quantity_received',
        'unit_price',
        'created_at',
    ]
    ordering = ['id']
    serializer_class = PurchaseOrderItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        po_param = self.request.query_params.get('purchase_order')
        if po_param:
            if po_param.isdigit():
                queryset = queryset.filter(purchase_order_id=po_param)
            else:
                queryset = queryset.filter(purchase_order__po_number__iexact=po_param.strip())

        part_param = self.request.query_params.get('spare_part')
        if part_param:
            if part_param.isdigit():
                queryset = queryset.filter(spare_part_id=part_param)
            else:
                queryset = queryset.filter(spare_part__part_number__iexact=part_param.strip())

        return queryset
