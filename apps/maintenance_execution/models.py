"""
Models for FlightFix Maintenance Execution & Documentation module.
"""

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.aircraft.models import Aircraft
from apps.maintenance_planning.models import MaintenanceTask
from apps.work_orders.models import WorkOrder


class ExecutionStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    PAUSED = 'PAUSED', _('Paused / Awaiting Parts')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class DocumentType(models.TextChoices):
    RELEASE_TO_SERVICE = 'RELEASE_TO_SERVICE', _('Certificate of Release to Service (CRS)')
    TASK_CHECKLIST = 'TASK_CHECKLIST', _('Maintenance Task Sign-off Checklist')
    INSPECTION_REPORT = 'INSPECTION_REPORT', _('Quality Assurance Inspection Report')
    NDT_REPORT = 'NDT_REPORT', _('Non-Destructive Testing (NDT) Report')
    MODIFICATION_APPROVAL = 'MODIFICATION_APPROVAL', _('Engineering Modification Approval')
    OTHER = 'OTHER', _('Other Technical Documentation')


class SignOffStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    SIGNED = 'SIGNED', _('Signed Off')
    VERIFIED = 'VERIFIED', _('Quality Verified')
    REJECTED = 'REJECTED', _('Rejected')


class MaintenanceExecution(models.Model):
    """
    Tracks real-time execution of maintenance work, labor hours, technician observations,
    and completion status for a specific work order.
    """
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='execution_records',
        verbose_name=_('work order'),
        help_text=_('Work order governing this maintenance execution.')
    )
    maintenance_task = models.ForeignKey(
        MaintenanceTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='execution_records',
        verbose_name=_('maintenance task'),
        help_text=_('Specific scheduled task being executed (if applicable).')
    )
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='maintenance_executions',
        verbose_name=_('aircraft'),
        help_text=_('Aircraft undergoing maintenance.')
    )
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_executions',
        verbose_name=_('executed by'),
        help_text=_('Technician performing the physical maintenance work.')
    )
    status = models.CharField(
        _('execution status'),
        max_length=25,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING,
        db_index=True
    )
    started_at = models.DateTimeField(
        _('started at'),
        null=True,
        blank=True,
        help_text=_('Timestamp when physical work commenced.')
    )
    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True,
        help_text=_('Timestamp when physical work finished.')
    )
    actual_labor_hours = models.DecimalField(
        _('actual labor hours'),
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'), message=_('Labor hours cannot be negative.'))],
        help_text=_('Total technician hours invested.')
    )
    work_performed = models.TextField(
        _('work performed'),
        help_text=_('Comprehensive technical narrative of disassembly, repairs, component tests, and reassembly.')
    )
    findings = models.TextField(
        _('discrepancies / findings'),
        blank=True,
        default='',
        help_text=_('Observations, wear indicators, corrosion, or abnormalities identified.')
    )
    corrective_actions = models.TextField(
        _('corrective actions taken'),
        blank=True,
        default='',
        help_text=_('Explicit engineering solutions implemented to resolve discrepancies.')
    )
    remarks = models.TextField(
        _('remarks / handover notes'),
        blank=True,
        default='',
        help_text=_('Technician remarks, tooling notes, or shift handover documentation.')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_executions',
        verbose_name=_('created by'),
        help_text=_('User who authorized/created this execution record.')
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
        verbose_name = _('Maintenance Execution Record')
        verbose_name_plural = _('Maintenance Execution Records')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
        ]

    def __str__(self):
        return f"Execution #{self.id} on {self.work_order.work_order_number} ({self.get_status_display()}) by {self.executed_by.username}"

    def clean(self):
        super().clean()
        errors = {}

        # 1. Negative labor hours validation
        if self.actual_labor_hours is not None and self.actual_labor_hours < Decimal('0.00'):
            errors['actual_labor_hours'] = _('Actual labor hours cannot be negative.')

        # 2. Timestamp order validation
        if self.started_at and self.completed_at:
            if self.completed_at < self.started_at:
                errors['completed_at'] = _('Completion timestamp cannot be prior to start timestamp.')

        # 3. Aircraft alignment validation
        if self.work_order_id and self.aircraft_id:
            if self.aircraft_id != self.work_order.aircraft_id:
                errors['aircraft'] = _('Selected aircraft must match the aircraft assigned to the work order.')

        # 4. Task schedule consistency check
        if self.work_order_id and self.maintenance_task_id:
            if (
                self.work_order.maintenance_schedule_id and
                self.maintenance_task.schedule_id != self.work_order.maintenance_schedule_id
            ):
                errors['maintenance_task'] = _(
                    'Selected task belongs to a different schedule than the work order.'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Auto-align aircraft with work_order if not explicitly given
        if self.work_order_id and not self.aircraft_id:
            self.aircraft = self.work_order.aircraft
        self.full_clean()
        super().save(*args, **kwargs)


class MaintenanceDocumentation(models.Model):
    """
    Stores technical sign-off certificates, compliance documentation, inspection checklists,
    and release-to-service records for completed maintenance execution.
    """
    execution = models.ForeignKey(
        MaintenanceExecution,
        on_delete=models.CASCADE,
        related_name='documentation_records',
        verbose_name=_('maintenance execution'),
        help_text=_('Maintenance execution record being documented.')
    )
    document_type = models.CharField(
        _('document type'),
        max_length=35,
        choices=DocumentType.choices,
        default=DocumentType.RELEASE_TO_SERVICE,
        db_index=True
    )
    document_number = models.CharField(
        _('document number'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique formal identifier (e.g., CRS-2026-0042, QA-INSP-901).')
    )
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Formal document or certificate title.')
    )
    issuing_authority = models.CharField(
        _('issuing authority'),
        max_length=150,
        help_text=_('Regulatory or internal quality authority (e.g. FAA / EASA / DGCA / Airline QA).')
    )
    document_reference = models.CharField(
        _('document reference / URL'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Electronic archive link, DMS reference, or physical file binder location.')
    )
    sign_off_status = models.CharField(
        _('sign-off status'),
        max_length=20,
        choices=SignOffStatus.choices,
        default=SignOffStatus.DRAFT,
        db_index=True
    )
    signed_off_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signed_documents',
        verbose_name=_('signed off by'),
        help_text=_('Authorized certifier / safety officer / QA inspector signing this record.')
    )
    signed_off_at = models.DateTimeField(
        _('signed off at'),
        null=True,
        blank=True,
        help_text=_('Timestamp of formal sign-off.')
    )
    remarks = models.TextField(
        _('remarks / compliance statement'),
        blank=True,
        default='',
        help_text=_('Release statements or certification notes.')
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
        verbose_name = _('Maintenance Documentation Record')
        verbose_name_plural = _('Maintenance Documentation Records')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_number']),
            models.Index(fields=['sign_off_status']),
            models.Index(fields=['document_type']),
        ]

    def __str__(self):
        return f"{self.document_number} - {self.title} ({self.get_sign_off_status_display()})"

    def clean(self):
        super().clean()
        errors = {}

        if self.document_number:
            self.document_number = self.document_number.strip().upper()

        # If signed off or verified, certifier should be specified
        if self.sign_off_status in (SignOffStatus.SIGNED, SignOffStatus.VERIFIED):
            if not self.signed_off_by_id:
                errors['signed_off_by'] = _('Sign-off certifier is required when status is Signed or Verified.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.document_number:
            self.document_number = self.document_number.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)
