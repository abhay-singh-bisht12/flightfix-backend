"""
Serializers for FlightFix Maintenance Planning & Scheduling module.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.aircraft.models import Aircraft
from apps.maintenance_planning.models import (
    MaintenanceSchedule,
    MaintenanceTask,
    MaintenanceType,
    MaintenancePriority,
    MaintenanceStatus,
    TaskStatus,
)

User = get_user_model()


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for individual maintenance tasks.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    schedule_title = serializers.CharField(source='schedule.title', read_only=True)
    aircraft_registration = serializers.CharField(
        source='schedule.aircraft.registration_number',
        read_only=True
    )

    class Meta:
        model = MaintenanceTask
        fields = (
            'id',
            'schedule',
            'schedule_title',
            'aircraft_registration',
            'task_name',
            'description',
            'task_order',
            'status',
            'status_display',
            'estimated_hours',
            'completed_at',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_task_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Task name cannot be blank.")
        return cleaned

    def validate_task_order(self, value):
        if value < 1:
            raise serializers.ValidationError("Task order must be 1 or greater.")
        return value

    def validate_status(self, value):
        if value not in TaskStatus.values:
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Allowed: {', '.join(TaskStatus.values)}"
            )
        return value

    def validate_estimated_hours(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Estimated hours cannot be negative.")
        return value


class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and managing maintenance schedules.
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
    maintenance_type_display = serializers.CharField(
        source='get_maintenance_type_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    tasks_count = serializers.IntegerField(
        source='tasks.count',
        read_only=True
    )

    class Meta:
        model = MaintenanceSchedule
        fields = (
            'id',
            'aircraft',
            'aircraft_registration',
            'aircraft_model',
            'title',
            'description',
            'maintenance_type',
            'maintenance_type_display',
            'priority',
            'priority_display',
            'planned_date',
            'due_date',
            'status',
            'status_display',
            'assigned_to',
            'assigned_to_username',
            'created_by',
            'created_by_username',
            'notes',
            'tasks_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def validate_title(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Title cannot be blank.")
        return cleaned

    def validate_maintenance_type(self, value):
        if value not in MaintenanceType.values:
            raise serializers.ValidationError(
                f"Invalid maintenance type '{value}'. Allowed: {', '.join(MaintenanceType.values)}"
            )
        return value

    def validate_priority(self, value):
        if value not in MaintenancePriority.values:
            raise serializers.ValidationError(
                f"Invalid priority '{value}'. Allowed: {', '.join(MaintenancePriority.values)}"
            )
        return value

    def validate_status(self, value):
        if value not in MaintenanceStatus.values:
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Allowed: {', '.join(MaintenanceStatus.values)}"
            )
        return value

    def validate(self, attrs):
        planned_date = attrs.get('planned_date')
        due_date = attrs.get('due_date')

        if self.instance:
            if planned_date is None and 'planned_date' not in attrs:
                planned_date = self.instance.planned_date
            if due_date is None and 'due_date' not in attrs:
                due_date = self.instance.due_date

        if planned_date and due_date:
            if due_date < planned_date:
                raise serializers.ValidationError({
                    'due_date': "Due date cannot be earlier than planned date."
                })

        return attrs


class MaintenanceScheduleDetailSerializer(MaintenanceScheduleSerializer):
    """
    Detailed maintenance schedule serializer with nested task list.
    """
    tasks = MaintenanceTaskSerializer(many=True, read_only=True)

    class Meta(MaintenanceScheduleSerializer.Meta):
        fields = MaintenanceScheduleSerializer.Meta.fields + ('tasks',)
