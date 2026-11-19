"""
Views and ViewSets for FlightFix Aircraft and Equipment APIs.
"""

from rest_framework import viewsets, filters
from apps.aircraft.models import Aircraft, Equipment
from apps.aircraft.pagination import StandardResultsSetPagination
from apps.aircraft.permissions import AircraftEquipmentPermission
from apps.aircraft.serializers import (
    AircraftSerializer,
    AircraftDetailSerializer,
    EquipmentSerializer,
)


class AircraftViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Aircraft fleet management.
    Supports search, status/manufacturer/type filtering, ordering, and pagination.
    """
    queryset = Aircraft.objects.prefetch_related('equipment').all()
    permission_classes = [AircraftEquipmentPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'registration_number',
        'model',
        'aircraft_type',
        'manufacturer',
        'serial_number',
    ]
    ordering_fields = [
        'registration_number',
        'model',
        'manufacturer',
        'status',
        'manufacture_date',
        'service_entry_date',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AircraftDetailSerializer
        return AircraftSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        manufacturer_param = self.request.query_params.get('manufacturer')
        if manufacturer_param:
            queryset = queryset.filter(manufacturer__icontains=manufacturer_param.strip())

        type_param = self.request.query_params.get('aircraft_type')
        if type_param:
            queryset = queryset.filter(aircraft_type__icontains=type_param.strip())

        model_param = self.request.query_params.get('model')
        if model_param:
            queryset = queryset.filter(model__icontains=model_param.strip())

        return queryset


class EquipmentViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Equipment component management.
    Supports search, status/manufacturer/type/aircraft filtering, ordering, and pagination.
    """
    queryset = Equipment.objects.select_related('aircraft').all()
    serializer_class = EquipmentSerializer
    permission_classes = [AircraftEquipmentPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'equipment_code',
        'name',
        'manufacturer',
        'serial_number',
        'location',
    ]
    ordering_fields = [
        'equipment_code',
        'name',
        'equipment_type',
        'manufacturer',
        'status',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())

        manufacturer_param = self.request.query_params.get('manufacturer')
        if manufacturer_param:
            queryset = queryset.filter(manufacturer__icontains=manufacturer_param.strip())

        type_param = self.request.query_params.get('equipment_type')
        if type_param:
            queryset = queryset.filter(equipment_type__iexact=type_param.strip())

        aircraft_param = self.request.query_params.get('aircraft')
        if aircraft_param:
            if aircraft_param.isdigit():
                queryset = queryset.filter(aircraft_id=aircraft_param)
            else:
                queryset = queryset.filter(aircraft__registration_number__iexact=aircraft_param.strip())

        return queryset
