"""
Serializers for FlightFix Aircraft and Equipment APIs.
"""

from rest_framework import serializers
from apps.aircraft.models import (
    Aircraft,
    AircraftStatus,
    Equipment,
    EquipmentStatus,
    EquipmentType,
)


class EquipmentSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for equipment when displayed inside aircraft details.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    equipment_type_display = serializers.CharField(source='get_equipment_type_display', read_only=True)

    class Meta:
        model = Equipment
        fields = (
            'id',
            'equipment_code',
            'name',
            'equipment_type',
            'equipment_type_display',
            'status',
            'status_display',
            'location',
        )


class AircraftSerializer(serializers.ModelSerializer):
    """
    Serializer for Aircraft list, create, update, and retrieve.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    equipment_count = serializers.IntegerField(source='equipment.count', read_only=True)

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
            'equipment_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_registration_number(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Registration number cannot be blank.")
        qs = Aircraft.objects.filter(registration_number__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An aircraft with this registration number already exists.")
        return cleaned

    def validate_serial_number(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Serial number cannot be blank.")
        qs = Aircraft.objects.filter(serial_number__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An aircraft with this serial number already exists.")
        return cleaned

    def validate_status(self, value):
        if value not in AircraftStatus.values:
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Allowed: {', '.join(AircraftStatus.values)}"
            )
        return value

    def validate(self, attrs):
        manufacture_date = attrs.get('manufacture_date')
        service_entry_date = attrs.get('service_entry_date')

        if self.instance:
            if manufacture_date is None and 'manufacture_date' not in attrs:
                manufacture_date = self.instance.manufacture_date
            if service_entry_date is None and 'service_entry_date' not in attrs:
                service_entry_date = self.instance.service_entry_date

        if manufacture_date and service_entry_date:
            if service_entry_date < manufacture_date:
                raise serializers.ValidationError({
                    'service_entry_date': "Service entry date cannot be earlier than manufacture date."
                })

        return attrs


class AircraftDetailSerializer(AircraftSerializer):
    """
    Detailed Aircraft representation with attached equipment list.
    """
    equipment = EquipmentSummarySerializer(many=True, read_only=True)

    class Meta(AircraftSerializer.Meta):
        fields = AircraftSerializer.Meta.fields + ('equipment',)


class EquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Equipment list, create, update, and retrieve.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    equipment_type_display = serializers.CharField(source='get_equipment_type_display', read_only=True)
    aircraft_registration = serializers.CharField(
        source='aircraft.registration_number',
        read_only=True
    )

    class Meta:
        model = Equipment
        fields = (
            'id',
            'equipment_code',
            'name',
            'equipment_type',
            'equipment_type_display',
            'manufacturer',
            'serial_number',
            'status',
            'status_display',
            'aircraft',
            'aircraft_registration',
            'location',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_equipment_code(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Equipment code cannot be blank.")
        qs = Equipment.objects.filter(equipment_code__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Equipment with this code already exists.")
        return cleaned

    def validate_equipment_type(self, value):
        if value not in EquipmentType.values:
            raise serializers.ValidationError(
                f"Invalid equipment type '{value}'. Allowed: {', '.join(EquipmentType.values)}"
            )
        return value

    def validate_status(self, value):
        if value not in EquipmentStatus.values:
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Allowed: {', '.join(EquipmentStatus.values)}"
            )
        return value
