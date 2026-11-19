"""
Serializers for FlightFix Maintenance Execution & Documentation module.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.maintenance_execution.models import (
    MaintenanceExecution,
    MaintenanceDocumentation,
    ExecutionStatus,
    SignOffStatus,
)


class MaintenanceDocumentationSerializer(serializers.ModelSerializer):
    """
    Serializer for technical sign-off and regulatory compliance documentation.
    """
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    sign_off_status_display = serializers.CharField(
        source='get_sign_off_status_display',
        read_only=True
    )
    signed_off_by_username = serializers.CharField(
        source='signed_off_by.username',
        read_only=True
    )
    execution_work_order_number = serializers.CharField(
        source='execution.work_order.work_order_number',
        read_only=True
    )

    class Meta:
        model = MaintenanceDocumentation
        fields = (
            'id',
            'execution',
            'execution_work_order_number',
            'document_type',
            'document_type_display',
            'document_number',
            'title',
            'issuing_authority',
            'document_reference',
            'sign_off_status',
            'sign_off_status_display',
            'signed_off_by',
            'signed_off_by_username',
            'signed_off_at',
            'remarks',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_document_number(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Document number cannot be blank.")
        qs = MaintenanceDocumentation.objects.filter(document_number__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A documentation record with this document number already exists.")
        return cleaned

    def validate(self, attrs):
        sign_off_status = attrs.get('sign_off_status') or (self.instance.sign_off_status if self.instance else None)
        signed_off_by = attrs.get('signed_off_by') or (self.instance.signed_off_by if self.instance else None)

        if sign_off_status in (SignOffStatus.SIGNED, SignOffStatus.VERIFIED) and not signed_off_by:
            raise serializers.ValidationError({
                'signed_off_by': "Sign-off certifier is required when status is Signed or Verified."
            })

        return attrs


class MaintenanceExecutionSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and creating Maintenance Execution Records.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    work_order_number = serializers.CharField(
        source='work_order.work_order_number',
        read_only=True
    )
    aircraft_registration = serializers.CharField(
        source='aircraft.registration_number',
        read_only=True
    )
    aircraft_model = serializers.CharField(
        source='aircraft.model',
        read_only=True
    )
    maintenance_task_name = serializers.CharField(
        source='maintenance_task.task_name',
        read_only=True
    )
    executed_by_username = serializers.CharField(
        source='executed_by.username',
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )

    class Meta:
        model = MaintenanceExecution
        fields = (
            'id',
            'work_order',
            'work_order_number',
            'maintenance_task',
            'maintenance_task_name',
            'aircraft',
            'aircraft_registration',
            'aircraft_model',
            'executed_by',
            'executed_by_username',
            'status',
            'status_display',
            'started_at',
            'completed_at',
            'actual_labor_hours',
            'work_performed',
            'findings',
            'corrective_actions',
            'remarks',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'aircraft', 'created_by', 'created_at', 'updated_at')

    def validate_actual_labor_hours(self, value):
        if value is not None and value < Decimal('0.00'):
            raise serializers.ValidationError("Actual labor hours cannot be negative.")
        return value

    def validate(self, attrs):
        started_at = attrs.get('started_at') or (self.instance.started_at if self.instance else None)
        completed_at = attrs.get('completed_at') or (self.instance.completed_at if self.instance else None)

        if started_at and completed_at and completed_at < started_at:
            raise serializers.ValidationError({
                'completed_at': "Completion timestamp cannot be prior to start timestamp."
            })

        work_order = attrs.get('work_order') or (self.instance.work_order if self.instance else None)
        maintenance_task = attrs.get('maintenance_task') or (self.instance.maintenance_task if self.instance else None)

        if work_order and maintenance_task:
            if work_order.maintenance_schedule and maintenance_task.schedule_id != work_order.maintenance_schedule_id:
                raise serializers.ValidationError({
                    'maintenance_task': "Selected task belongs to a different schedule than the work order."
                })

        return attrs


class MaintenanceExecutionDetailSerializer(MaintenanceExecutionSerializer):
    """
    Detailed serializer including linked compliance and sign-off documentation records.
    """
    documentation_records = MaintenanceDocumentationSerializer(many=True, read_only=True)

    class Meta(MaintenanceExecutionSerializer.Meta):
        fields = MaintenanceExecutionSerializer.Meta.fields + ('documentation_records',)
