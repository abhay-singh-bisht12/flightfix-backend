"""
Serializers for FlightFix Mobile / Field Technician Support module.
"""

from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.aircraft.models import Aircraft
from apps.compliance.models import ComplianceRecord
from apps.inventory.models import SparePart
from apps.maintenance_execution.models import (
    MaintenanceExecution,
    ExecutionStatus,
)
from apps.maintenance_planning.models import (
    MaintenanceSchedule,
    MaintenanceTask,
    TaskStatus,
)
from apps.work_orders.models import (
    WorkOrder,
    WorkOrderStatus,
)

User = get_user_model()


class TechnicianProfileSerializer(serializers.ModelSerializer):
    """
    Lightweight user profile representation for field technicians.
    """
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'name',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
        )
        read_only_fields = fields

    def get_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.username


class TechnicianSummarySerializer(serializers.Serializer):
    """
    Aggregate counts for technician dashboard.
    """
    assigned_schedules = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    open_work_orders = serializers.IntegerField()
    pending_compliance = serializers.IntegerField()


class TechnicianTaskSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for maintenance tasks assigned to the technician.
    """
    schedule_title = serializers.CharField(source='schedule.title', read_only=True)
    aircraft_registration = serializers.CharField(source='schedule.aircraft.registration_number', read_only=True)
    aircraft_model = serializers.CharField(source='schedule.aircraft.model', read_only=True)
    planned_date = serializers.DateField(source='schedule.planned_date', read_only=True)
    due_date = serializers.DateField(source='schedule.due_date', read_only=True)
    priority = serializers.CharField(source='schedule.priority', read_only=True)
    priority_display = serializers.CharField(source='schedule.get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = MaintenanceTask
        fields = (
            'id',
            'schedule',
            'schedule_title',
            'aircraft_registration',
            'aircraft_model',
            'task_name',
            'description',
            'task_order',
            'status',
            'status_display',
            'estimated_hours',
            'completed_at',
            'notes',
            'planned_date',
            'due_date',
            'priority',
            'priority_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TechnicianWorkOrderSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for work orders assigned to the logged-in technician.
    """
    aircraft_registration = serializers.CharField(source='aircraft.registration_number', read_only=True)
    aircraft_model = serializers.CharField(source='aircraft.model', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    work_order_type_display = serializers.CharField(source='get_work_order_type_display', read_only=True)
    maintenance_schedule_title = serializers.CharField(source='maintenance_schedule.title', read_only=True)

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
            'created_by',
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
        read_only_fields = fields


class TechnicianWorkOrderUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer enforcing safe technician updates to work orders.
    Technicians can update execution fields (status, actual_hours, findings, corrective_action,
    notes, actual_start_date, actual_completion_date), while administrative and assignment
    fields are strictly protected from modification.
    """
    status = serializers.ChoiceField(choices=WorkOrderStatus.choices, required=False)
    actual_hours = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    findings = serializers.CharField(required=False, allow_blank=True)
    corrective_action = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    actual_start_date = serializers.DateField(required=False, allow_null=True)
    actual_completion_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = WorkOrder
        fields = (
            'id',
            'work_order_number',
            'aircraft',
            'maintenance_schedule',
            'title',
            'description',
            'work_order_type',
            'priority',
            'status',
            'assigned_to',
            'created_by',
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
        read_only_fields = (
            'id',
            'work_order_number',
            'aircraft',
            'maintenance_schedule',
            'title',
            'description',
            'work_order_type',
            'priority',
            'assigned_to',
            'created_by',
            'planned_start_date',
            'planned_completion_date',
            'estimated_hours',
            'created_at',
            'updated_at',
        )

    def validate(self, attrs):
        # Explicit tamper detection: reject malicious attempts to alter protected fields
        initial_data = getattr(self, 'initial_data', {})
        protected_fields = [
            'assigned_to', 'aircraft', 'created_by', 'priority',
            'work_order_number', 'work_order_type', 'maintenance_schedule',
            'planned_start_date', 'planned_completion_date', 'estimated_hours',
        ]
        for field in protected_fields:
            if field in initial_data:
                current_val = getattr(self.instance, field, None)
                incoming_val = initial_data[field]
                if hasattr(current_val, 'pk'):
                    current_val = current_val.pk
                if current_val is not None and str(incoming_val) != str(current_val):
                    raise serializers.ValidationError({
                        field: f"Field technicians are not permitted to modify '{field}'."
                    })

        instance = self.instance
        actual_start_date = attrs.get('actual_start_date', instance.actual_start_date)
        actual_completion_date = attrs.get('actual_completion_date', instance.actual_completion_date)
        if actual_start_date and actual_completion_date and actual_completion_date < actual_start_date:
            raise serializers.ValidationError({
                'actual_completion_date': "Actual completion date cannot be before actual start date."
            })

        actual_hours = attrs.get('actual_hours', instance.actual_hours)
        if actual_hours is not None and actual_hours < Decimal('0'):
            raise serializers.ValidationError({
                'actual_hours': "Actual hours cannot be negative."
            })

        return attrs


class TechnicianExecutionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for maintenance executions performed by the logged-in technician.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    work_order_number = serializers.CharField(source='work_order.work_order_number', read_only=True)
    aircraft_registration = serializers.CharField(source='aircraft.registration_number', read_only=True)
    aircraft_model = serializers.CharField(source='aircraft.model', read_only=True)
    maintenance_task_name = serializers.CharField(source='maintenance_task.task_name', read_only=True)
    executed_by_username = serializers.CharField(source='executed_by.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

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
        read_only_fields = fields


class TechnicianExecutionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a maintenance execution record for a technician's assigned work.
    """
    class Meta:
        model = MaintenanceExecution
        fields = (
            'id',
            'work_order',
            'maintenance_task',
            'status',
            'started_at',
            'completed_at',
            'actual_labor_hours',
            'work_performed',
            'findings',
            'corrective_actions',
            'remarks',
        )
        read_only_fields = ('id',)

    def validate_work_order(self, value):
        user = self.context['request'].user
        if value.assigned_to_id != user.id:
            raise serializers.ValidationError(
                "You can only log maintenance execution records for work orders assigned to you."
            )
        return value

    def validate_actual_labor_hours(self, value):
        if value is not None and value < Decimal('0.00'):
            raise serializers.ValidationError("Actual labor hours cannot be negative.")
        return value

    def validate(self, attrs):
        started_at = attrs.get('started_at')
        completed_at = attrs.get('completed_at')
        if started_at and completed_at and completed_at < started_at:
            raise serializers.ValidationError({
                'completed_at': "Completion timestamp cannot be prior to start timestamp."
            })

        work_order = attrs.get('work_order')
        maintenance_task = attrs.get('maintenance_task')
        if work_order and maintenance_task:
            if work_order.maintenance_schedule_id and maintenance_task.schedule_id != work_order.maintenance_schedule_id:
                raise serializers.ValidationError({
                    'maintenance_task': "Selected task belongs to a different schedule than the work order."
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        work_order = validated_data['work_order']
        validated_data['aircraft'] = work_order.aircraft
        validated_data['executed_by'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)


class TechnicianExecutionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for safe updates to maintenance executions by the executing technician.
    """
    class Meta:
        model = MaintenanceExecution
        fields = (
            'id',
            'work_order',
            'aircraft',
            'maintenance_task',
            'executed_by',
            'status',
            'started_at',
            'completed_at',
            'actual_labor_hours',
            'work_performed',
            'findings',
            'corrective_actions',
            'remarks',
            'created_by',
        )
        read_only_fields = (
            'id',
            'work_order',
            'aircraft',
            'maintenance_task',
            'executed_by',
            'created_by',
        )

    def validate_actual_labor_hours(self, value):
        if value is not None and value < Decimal('0.00'):
            raise serializers.ValidationError("Actual labor hours cannot be negative.")
        return value

    def validate(self, attrs):
        started_at = attrs.get('started_at', self.instance.started_at)
        completed_at = attrs.get('completed_at', self.instance.completed_at)
        if started_at and completed_at and completed_at < started_at:
            raise serializers.ValidationError({
                'completed_at': "Completion timestamp cannot be prior to start timestamp."
            })
        return attrs


class TechnicianAircraftSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for aircraft relevant to technician assignments.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Aircraft
        fields = (
            'id',
            'registration_number',
            'aircraft_type',
            'model',
            'manufacturer',
            'serial_number',
            'status',
            'status_display',
            'manufacture_date',
            'service_entry_date',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TechnicianComplianceRecordSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for compliance records relevant to technician assignments.
    """
    requirement_code = serializers.CharField(source='requirement.requirement_code', read_only=True)
    requirement_title = serializers.CharField(source='requirement.title', read_only=True)
    regulation_type = serializers.CharField(source='requirement.regulation_type', read_only=True)
    issuing_authority = serializers.CharField(source='requirement.issuing_authority', read_only=True)
    due_date = serializers.DateField(source='requirement.due_date', read_only=True)
    aircraft_registration = serializers.CharField(source='aircraft.registration_number', read_only=True)
    aircraft_model = serializers.CharField(source='aircraft.model', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)

    class Meta:
        model = ComplianceRecord
        fields = (
            'id',
            'requirement',
            'requirement_code',
            'requirement_title',
            'regulation_type',
            'issuing_authority',
            'due_date',
            'aircraft',
            'aircraft_registration',
            'aircraft_model',
            'maintenance_execution',
            'verification_status',
            'verification_status_display',
            'verified_by',
            'verified_by_username',
            'verified_at',
            'evidence_reference',
            'findings',
            'corrective_action',
            'remarks',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TechnicianAvailablePartSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for spare parts inventory needed by technicians.
    Strictly excludes vendor, unit price, and purchasing data.
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

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
            'location',
            'status',
            'status_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TechnicianDashboardSerializer(serializers.Serializer):
    """
    Composite serializer assembling the compact mobile dashboard for technicians.
    """
    technician = TechnicianProfileSerializer()
    summary = TechnicianSummarySerializer()
    assigned_aircraft = TechnicianAircraftSerializer(many=True)
    tasks = TechnicianTaskSerializer(many=True)
    work_orders = TechnicianWorkOrderSerializer(many=True)
    recent_executions = TechnicianExecutionSerializer(many=True)
