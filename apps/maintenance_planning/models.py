"""
Models for FlightFix Maintenance Planning & Scheduling module.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.aircraft.models import Aircraft


class MaintenanceType(models.TextChoices):
    PREVENTIVE = 'PREVENTIVE', _('Preventive')
    CORRECTIVE = 'CORRECTIVE', _('Corrective')
    INSPECTION = 'INSPECTION', _('Inspection')
    OVERHAUL = 'OVERHAUL', _('Overhaul')


class MaintenancePriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class MaintenanceStatus(models.TextChoices):
    PLANNED = 'PLANNED', _('Planned')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    SKIPPED = 'SKIPPED', _('Skipped')


class MaintenanceSchedule(models.Model):
    """
    Represents a planned or active maintenance event/cycle for an aircraft.
    """
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules',
        verbose_name=_('aircraft'),
        help_text=_('Aircraft requiring maintenance.')
    )
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Brief summary of the maintenance event.')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
        help_text=_('Detailed scope of maintenance work.')
    )
    maintenance_type = models.CharField(
        _('maintenance type'),
        max_length=30,
        choices=MaintenanceType.choices,
        default=MaintenanceType.PREVENTIVE,
        db_index=True
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=MaintenancePriority.choices,
        default=MaintenancePriority.MEDIUM,
        db_index=True
    )
    planned_date = models.DateField(
        _('planned date'),
        db_index=True,
        help_text=_('Scheduled start date.')
    )
    due_date = models.DateField(
        _('due date'),
        db_index=True,
        help_text=_('Latest acceptable completion date.')
    )
    status = models.CharField(
        _('status'),
        max_length=30,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.PLANNED,
        db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_maintenance_schedules',
        verbose_name=_('assigned lead/technician'),
        help_text=_('Technician or lead assigned to supervise this schedule.')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_maintenance_schedules',
        verbose_name=_('created by')
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
        db_table = 'maintenance_schedules'
        ordering = ['-created_at']
        verbose_name = _('maintenance schedule')
        verbose_name_plural = _('maintenance schedules')
        indexes = [
            models.Index(fields=['status', 'priority'], name='idx_maint_status_priority'),
            models.Index(fields=['planned_date', 'due_date'], name='idx_maint_dates'),
        ]

    def clean(self):
        super().clean()
        if self.title:
            self.title = self.title.strip()
        if self.planned_date and self.due_date:
            if self.due_date < self.planned_date:
                raise ValidationError({
                    'due_date': _('Due date cannot be before planned date.')
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.aircraft.registration_number}) - {self.get_status_display()}"


class MaintenanceTask(models.Model):
    """
    Individual step, check, or task within a maintenance schedule.
    """
    schedule = models.ForeignKey(
        MaintenanceSchedule,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('maintenance schedule')
    )
    task_name = models.CharField(
        _('task name'),
        max_length=200,
        help_text=_('Name or brief title of this task/inspection step.')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default=''
    )
    task_order = models.PositiveIntegerField(
        _('task order'),
        default=1,
        help_text=_('Sequence order of this task in the schedule.')
    )
    status = models.CharField(
        _('status'),
        max_length=30,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True
    )
    estimated_hours = models.DecimalField(
        _('estimated hours'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Estimated duration in labor hours.')
    )
    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True
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
        db_table = 'maintenance_tasks'
        ordering = ['task_order', 'id']
        verbose_name = _('maintenance task')
        verbose_name_plural = _('maintenance tasks')
        indexes = [
            models.Index(fields=['schedule', 'task_order'], name='idx_task_sched_order'),
            models.Index(fields=['status'], name='idx_task_status'),
        ]

    def clean(self):
        super().clean()
        if self.task_name:
            self.task_name = self.task_name.strip()
        if self.estimated_hours is not None and self.estimated_hours < 0:
            raise ValidationError({
                'estimated_hours': _('Estimated hours cannot be negative.')
            })
        if self.status == TaskStatus.COMPLETED and self.completed_at is None:
            self.completed_at = timezone.now()
        elif self.status != TaskStatus.COMPLETED and self.completed_at is not None:
            # If changed back from completed, clear completed_at
            pass

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Step {self.task_order}: {self.task_name} ({self.get_status_display()})"
