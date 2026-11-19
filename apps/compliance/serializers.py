"""
Serializers for FlightFix Airworthiness & Regulatory Compliance module.
"""

from rest_framework import serializers

from apps.compliance.models import (
    ComplianceRequirement,
    ComplianceRecord,
    RequirementStatus,
    VerificationStatus,
)


class ComplianceRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for Compliance Verification Records.
    """
    requirement_code = serializers.CharField(
        source='requirement.requirement_code',
        read_only=True
    )
    requirement_title = serializers.CharField(
        source='requirement.title',
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
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )
    verified_by_username = serializers.CharField(
        source='verified_by.username',
        read_only=True
    )

    class Meta:
        model = ComplianceRecord
        fields = (
            'id',
            'requirement',
            'requirement_code',
            'requirement_title',
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
        read_only_fields = ('id', 'aircraft', 'created_at', 'updated_at')

    def validate(self, attrs):
        requirement = attrs.get('requirement') or (self.instance.requirement if self.instance else None)
        status_val = attrs.get('verification_status') or (self.instance.verification_status if self.instance else None)
        verified_by = attrs.get('verified_by') or (self.instance.verified_by if self.instance else None)
        exec_obj = attrs.get('maintenance_execution') or (self.instance.maintenance_execution if self.instance else None)

        # 1. Verification requirements
        if status_val == VerificationStatus.VERIFIED and not verified_by:
            raise serializers.ValidationError({
                'verified_by': "Verified compliance records must specify a verified_by user."
            })

        # 2. Execution aircraft match
        if exec_obj and requirement:
            if exec_obj.aircraft_id != requirement.aircraft_id:
                raise serializers.ValidationError({
                    'maintenance_execution': "Maintenance execution belongs to a different aircraft than the compliance requirement."
                })

        return attrs


class ComplianceRequirementSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and creating Compliance Requirements.
    """
    aircraft_registration = serializers.CharField(
        source='aircraft.registration_number',
        read_only=True
    )
    aircraft_model = serializers.CharField(
        source='aircraft.model',
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
    regulation_type_display = serializers.CharField(
        source='get_regulation_type_display',
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

    class Meta:
        model = ComplianceRequirement
        fields = (
            'id',
            'requirement_code',
            'title',
            'description',
            'regulation_type',
            'regulation_type_display',
            'issuing_authority',
            'aircraft',
            'aircraft_registration',
            'aircraft_model',
            'effective_date',
            'due_date',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'assigned_to',
            'assigned_to_username',
            'notes',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def validate_requirement_code(self, value):
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Requirement code cannot be blank.")
        qs = ComplianceRequirement.objects.filter(requirement_code__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A compliance requirement with this code already exists.")
        return cleaned

    def validate(self, attrs):
        effective_date = attrs.get('effective_date') or (self.instance.effective_date if self.instance else None)
        due_date = attrs.get('due_date') or (self.instance.due_date if self.instance else None)

        if effective_date and due_date and due_date < effective_date:
            raise serializers.ValidationError({
                'due_date': "Compliance due date cannot be prior to effective date."
            })

        return attrs


class ComplianceRequirementDetailSerializer(ComplianceRequirementSerializer):
    """
    Detailed serializer including linked compliance verification records.
    """
    compliance_records = ComplianceRecordSerializer(many=True, read_only=True)

    class Meta(ComplianceRequirementSerializer.Meta):
        fields = ComplianceRequirementSerializer.Meta.fields + ('compliance_records',)
