"""
Serializers for FlightFix Work Order Management module.
"""

from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.aircraft.models import Aircraft
from apps.maintenance_planning.models import MaintenanceSchedule
from apps.work_orders.models import (
    WorkOrder,
    WorkOrderType,
    WorkOrderPriority,
    WorkOrderStatus,
)

User = get_user_model()


class WorkOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and managing Work Orders.
    """
    aircraft_registration = serializers.CharField(
        source='aircraft.registration_number',
        read_only=True
    )
    aircraft_model = serializers.CharField(
        source='aircraft.model',
        read_only=True
    )
    assigned_to_username = serializers.CharField(
        source='assigned_to.username',
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    maintenance_schedule_title = serializers.CharField(
        source='maintenance_schedule.title',
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
    work_order_type_display = serializers.CharField(
        source='get_work_order_type_display',
        read_only=True
    )

    class Meta:
        model = WorkOrder
        fields = (
            'id',
            'work_order_number',
            'aircraft',
            'aircraft_registration',
            'aircraft_model',
            'maintenance_schedule',
            'maintenance_schedule_title',
            'title',
            'description',
            'work_order_type',
            'work_order_type_display',
            'priority',
            'priority_display',
            'status',
            'status_display',
            'assigned_to',
            'assigned_to_username',
            'created_by',
            'created_by_username',
            'planned_start_date',
            'planned_completion_date',
            'actual_start_date',
            'actual_completion_date',
            'estimated_hours',
            'actual_hours',
            'findings',
            'corrective_action',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def validate_work_order_number(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Work order number cannot be blank.")
        qs = WorkOrder.objects.filter(work_order_number__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A work order with this number already exists.")
        return cleaned

    def validate_title(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Title cannot be blank.")
        return cleaned

    def validate_work_order_type(self, value):
        if value not in WorkOrderType.values:
            raise serializers.ValidationError(
                f"Invalid work order type '{value}'. Allowed: {', '.join(WorkOrderType.values)}"
            )
        return value

    def validate_priority(self, value):
        if value not in WorkOrderPriority.values:
            raise serializers.ValidationError(
                f"Invalid priority '{value}'. Allowed: {', '.join(WorkOrderPriority.values)}"
            )
        return value

    def validate_status(self, value):
        if value not in WorkOrderStatus.values:
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Allowed: {', '.join(WorkOrderStatus.values)}"
            )
        return value

    def validate_estimated_hours(self, value):
        if value is not None and value < Decimal('0'):
            raise serializers.ValidationError("Estimated hours cannot be negative.")
        return value

    def validate_actual_hours(self, value):
        if value is not None and value < Decimal('0'):
            raise serializers.ValidationError("Actual hours cannot be negative.")
        return value

    def validate(self, attrs):
        # Planned dates validation
        planned_start_date = attrs.get('planned_start_date')
        planned_completion_date = attrs.get('planned_completion_date')

        if self.instance:
            if planned_start_date is None and 'planned_start_date' not in attrs:
                planned_start_date = self.instance.planned_start_date
            if planned_completion_date is None and 'planned_completion_date' not in attrs:
                planned_completion_date = self.instance.planned_completion_date

        if planned_start_date and planned_completion_date:
            if planned_completion_date < planned_start_date:
                raise serializers.ValidationError({
                    'planned_completion_date': "Planned completion date cannot be before planned start date."
                })

        # Actual dates validation
        actual_start_date = attrs.get('actual_start_date')
        actual_completion_date = attrs.get('actual_completion_date')

        if self.instance:
            if actual_start_date is None and 'actual_start_date' not in attrs:
                actual_start_date = self.instance.actual_start_date
            if actual_completion_date is None and 'actual_completion_date' not in attrs:
                actual_completion_date = self.instance.actual_completion_date

        if actual_start_date and actual_completion_date:
            if actual_completion_date < actual_start_date:
                raise serializers.ValidationError({
                    'actual_completion_date': "Actual completion date cannot be before actual start date."
                })

        return attrs


class WorkOrderDetailSerializer(WorkOrderSerializer):
    """
    Detailed serializer for single Work Order retrieve view.
    """
    pass
