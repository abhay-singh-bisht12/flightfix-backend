"""
Models for FlightFix Work Order Management module.
"""

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.aircraft.models import Aircraft
from apps.maintenance_planning.models import MaintenanceSchedule


class WorkOrderType(models.TextChoices):
    PREVENTIVE = 'PREVENTIVE', _('Preventive')
    CORRECTIVE = 'CORRECTIVE', _('Corrective')
    INSPECTION = 'INSPECTION', _('Inspection')
    EMERGENCY = 'EMERGENCY', _('Emergency')


class WorkOrderPriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class WorkOrderStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    ASSIGNED = 'ASSIGNED', _('Assigned')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    ON_HOLD = 'ON_HOLD', _('On Hold')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class WorkOrder(models.Model):
    """
    Represents an authorized maintenance work order for an aircraft.
    """
    work_order_number = models.CharField(
        _('work order number'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique work order identifier (e.g., WO-2026-0001).')
    )
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='work_orders',
        verbose_name=_('aircraft'),
        help_text=_('Aircraft associated with this work order.')
    )
    maintenance_schedule = models.ForeignKey(
        MaintenanceSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name=_('maintenance schedule'),
        help_text=_('Optional maintenance schedule this work order fulfills.')
    )
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Brief summary of the maintenance work.')
    )
    description = models.TextField(
        _('description'),
        help_text=_('Detailed instructions and scope of work.')
    )
    work_order_type = models.CharField(
        _('work order type'),
        max_length=30,
        choices=WorkOrderType.choices,
        default=WorkOrderType.CORRECTIVE,
        db_index=True
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=WorkOrderPriority.choices,
        default=WorkOrderPriority.MEDIUM,
        db_index=True
    )
    status = models.CharField(
        _('status'),
        max_length=30,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.OPEN,
        db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_work_orders',
        verbose_name=_('assigned technician'),
        help_text=_('Technician assigned to execute this work order.')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_work_orders',
        verbose_name=_('created by')
    )
    planned_start_date = models.DateField(
        _('planned start date'),
        null=True,
        blank=True,
        db_index=True
    )
    planned_completion_date = models.DateField(
        _('planned completion date'),
        null=True,
        blank=True
    )
    actual_start_date = models.DateField(
        _('actual start date'),
        null=True,
        blank=True
    )
    actual_completion_date = models.DateField(
        _('actual completion date'),
        null=True,
        blank=True
    )
    estimated_hours = models.DecimalField(
        _('estimated hours'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Estimated labor hours.')
    )
    actual_hours = models.DecimalField(
        _('actual hours'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Actual labor hours logged.')
    )
    findings = models.TextField(
        _('findings'),
        blank=True,
        default='',
        help_text=_('Observations and defect descriptions found during inspection.')
    )
    corrective_action = models.TextField(
        _('corrective action'),
        blank=True,
        default='',
        help_text=_('Detailed repair and maintenance steps taken.')
    )
    notes = models.TextField(
        _('notes'),
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
        db_table = 'work_orders'
        ordering = ['-created_at']
        verbose_name = _('work order')
        verbose_name_plural = _('work orders')
        indexes = [
            models.Index(fields=['status', 'priority'], name='idx_wo_status_priority'),
            models.Index(fields=['planned_start_date', 'planned_completion_date'], name='idx_wo_planned_dates'),
        ]

    def clean(self):
        super().clean()
        if self.work_order_number:
            self.work_order_number = self.work_order_number.strip().upper()
        if self.title:
            self.title = self.title.strip()

        # Date validations
        if self.planned_start_date and self.planned_completion_date:
            if self.planned_completion_date < self.planned_start_date:
                raise ValidationError({
                    'planned_completion_date': _('Planned completion date cannot be before planned start date.')
                })

        if self.actual_start_date and self.actual_completion_date:
            if self.actual_completion_date < self.actual_start_date:
                raise ValidationError({
                    'actual_completion_date': _('Actual completion date cannot be before actual start date.')
                })

        # Numeric validations
        if self.estimated_hours is not None and self.estimated_hours < Decimal('0'):
            raise ValidationError({
                'estimated_hours': _('Estimated hours cannot be negative.')
            })

        if self.actual_hours is not None and self.actual_hours < Decimal('0'):
            raise ValidationError({
                'actual_hours': _('Actual hours cannot be negative.')
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.work_order_number} - {self.title} ({self.get_status_display()})"
