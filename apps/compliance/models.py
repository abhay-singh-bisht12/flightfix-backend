"""
Models for FlightFix Airworthiness & Regulatory Compliance module.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.aircraft.models import Aircraft
from apps.maintenance_execution.models import MaintenanceExecution


class RequirementStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLIANT = 'COMPLIANT', _('Compliant')
    NON_COMPLIANT = 'NON_COMPLIANT', _('Non-Compliant')
    EXPIRED = 'EXPIRED', _('Expired')


class RequirementPriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class RegulationType(models.TextChoices):
    AIRWORTHINESS_DIRECTIVE = 'AIRWORTHINESS_DIRECTIVE', _('Airworthiness Directive (AD)')
    SERVICE_BULLETIN = 'SERVICE_BULLETIN', _('Service Bulletin (SB)')
    INSPECTION_REQUIREMENT = 'INSPECTION_REQUIREMENT', _('Inspection Requirement')
    SAFETY_REQUIREMENT = 'SAFETY_REQUIREMENT', _('Safety Requirement')
    INTERNAL_POLICY = 'INTERNAL_POLICY', _('Internal Policy')
    OTHER = 'OTHER', _('Other Regulatory Mandate')


class VerificationStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    VERIFIED = 'VERIFIED', _('Verified')
    FAILED = 'FAILED', _('Failed')
    WAIVED = 'WAIVED', _('Waived')


class ComplianceRequirement(models.Model):
    """
    Represents an airworthiness directive, service bulletin, or safety mandate
    applicable to an aircraft.
    """
    requirement_code = models.CharField(
        _('requirement code'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique formal code (e.g., AD-2026-FAA-01, SB-A320-57-1024).')
    )
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Descriptive summary of the regulatory mandate.')
    )
    description = models.TextField(
        _('description'),
        help_text=_('Detailed compliance instructions and scope of directive.')
    )
    regulation_type = models.CharField(
        _('regulation type'),
        max_length=40,
        choices=RegulationType.choices,
        default=RegulationType.AIRWORTHINESS_DIRECTIVE,
        db_index=True
    )
    issuing_authority = models.CharField(
        _('issuing authority'),
        max_length=150,
        db_index=True,
        help_text=_('Regulatory body (e.g. FAA / EASA / DGCA / Boeing / Airbus).')
    )
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='compliance_requirements',
        verbose_name=_('aircraft'),
        help_text=_('Aircraft subject to this compliance requirement.')
    )
    effective_date = models.DateField(
        _('effective date'),
        help_text=_('Date when the regulation becomes legally binding.')
    )
    due_date = models.DateField(
        _('compliance due date'),
        help_text=_('Latest date by which compliance action must be completed.')
    )
    status = models.CharField(
        _('status'),
        max_length=25,
        choices=RequirementStatus.choices,
        default=RequirementStatus.OPEN,
        db_index=True
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=RequirementPriority.choices,
        default=RequirementPriority.HIGH,
        db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_compliance_requirements',
        verbose_name=_('assigned to'),
        help_text=_('Safety Officer or engineer assigned to oversee compliance.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default='',
        help_text=_('Additional implementation notes or engineering instructions.')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_compliance_requirements',
        verbose_name=_('created by')
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('Compliance Requirement')
        verbose_name_plural = _('Compliance Requirements')
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['requirement_code']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['due_date']),
            models.Index(fields=['regulation_type']),
        ]

    def __str__(self):
        return f"{self.requirement_code}: {self.title} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        errors = {}

        if self.requirement_code:
            self.requirement_code = self.requirement_code.strip().upper()

        if self.effective_date and self.due_date:
            if self.due_date < self.effective_date:
                errors['due_date'] = _('Compliance due date cannot be prior to effective date.')

        if errors:
            raise ValidationError(errors)

    def check_and_update_expired(self):
        """
        Automatically sets status to EXPIRED if due_date has elapsed and the requirement is not COMPLIANT.
        """
        if self.due_date and self.due_date < timezone.now().date():
            if self.status not in (RequirementStatus.COMPLIANT, RequirementStatus.EXPIRED):
                self.status = RequirementStatus.EXPIRED

    def save(self, *args, **kwargs):
        if self.requirement_code:
            self.requirement_code = self.requirement_code.strip().upper()
        self.check_and_update_expired()
        self.full_clean()
        super().save(*args, **kwargs)


class ComplianceRecord(models.Model):
    """
    Verifies and audits physical execution or evidence satisfying a ComplianceRequirement.
    """
    requirement = models.ForeignKey(
        ComplianceRequirement,
        on_delete=models.CASCADE,
        related_name='compliance_records',
        verbose_name=_('compliance requirement'),
        help_text=_('Regulatory requirement verified by this record.')
    )
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='compliance_records',
        verbose_name=_('aircraft'),
        help_text=_('Aircraft verified (must match requirement aircraft).')
    )
    maintenance_execution = models.ForeignKey(
        MaintenanceExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_records',
        verbose_name=_('maintenance execution'),
        help_text=_('Optional maintenance execution record providing proof of compliance.')
    )
    verification_status = models.CharField(
        _('verification status'),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_compliance_records',
        verbose_name=_('verified by'),
        help_text=_('Safety Officer or authorized airworthiness certifier.')
    )
    verified_at = models.DateTimeField(
        _('verified at'),
        null=True,
        blank=True,
        help_text=_('Timestamp of physical verification.')
    )
    evidence_reference = models.CharField(
        _('evidence reference'),
        max_length=255,
        help_text=_('Logbook entry #, CRS certificate #, or DMS URL.')
    )
    findings = models.TextField(
        _('findings'),
        blank=True,
        default='',
        help_text=_('Observations, non-conformities, or measurement deviations.')
    )
    corrective_action = models.TextField(
        _('corrective action'),
        blank=True,
        default='',
        help_text=_('Rectification steps taken if initial check failed.')
    )
    remarks = models.TextField(
        _('remarks'),
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('Compliance Record')
        verbose_name_plural = _('Compliance Records')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['verification_status']),
            models.Index(fields=['verified_at']),
        ]

    def __str__(self):
        return f"Verification #{self.id} for {self.requirement.requirement_code} - {self.get_verification_status_display()}"

    def clean(self):
        super().clean()
        errors = {}

        # Auto-align aircraft with requirement if not set
        if self.requirement_id and not self.aircraft_id:
            self.aircraft = self.requirement.aircraft
        elif self.requirement_id and self.aircraft_id:
            if self.aircraft_id != self.requirement.aircraft_id:
                errors['aircraft'] = _('Aircraft must match the aircraft targeted by the compliance requirement.')

        # Cross-validate maintenance execution aircraft
        if self.maintenance_execution_id and self.aircraft_id:
            if self.maintenance_execution.aircraft_id != self.aircraft_id:
                errors['maintenance_execution'] = _(
                    'Selected maintenance execution belongs to a different aircraft than this compliance record.'
                )

        # Verification constraints
        if self.verification_status == VerificationStatus.VERIFIED:
            if not self.verified_by_id:
                errors['verified_by'] = _('Verified compliance records must specify a verified_by user.')
            if not self.verified_at:
                self.verified_at = timezone.now()

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.requirement_id and not self.aircraft_id:
            self.aircraft = self.requirement.aircraft
        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)
            # If successfully VERIFIED, transition requirement to COMPLIANT
            if self.verification_status == VerificationStatus.VERIFIED:
                req = self.requirement
                if req.status != RequirementStatus.COMPLIANT:
                    req.status = RequirementStatus.COMPLIANT
                    req.save()
