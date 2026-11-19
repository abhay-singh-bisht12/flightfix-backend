"""
Models for FlightFix Aircraft and Equipment Management (Epic P05-E04).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class AircraftStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    MAINTENANCE = 'MAINTENANCE', _('Under Maintenance')
    GROUNDED = 'GROUNDED', _('Grounded')
    RETIRED = 'RETIRED', _('Retired')


class EquipmentType(models.TextChoices):
    ENGINE = 'ENGINE', _('Engine')
    AVIONICS = 'AVIONICS', _('Avionics')
    LANDING_GEAR = 'LANDING_GEAR', _('Landing Gear')
    HYDRAULICS = 'HYDRAULICS', _('Hydraulics')
    SAFETY = 'SAFETY', _('Safety Equipment')
    APU = 'APU', _('Auxiliary Power Unit')
    OTHER = 'OTHER', _('Other')


class EquipmentStatus(models.TextChoices):
    OPERATIONAL = 'OPERATIONAL', _('Operational')
    UNDER_MAINTENANCE = 'UNDER_MAINTENANCE', _('Under Maintenance')
    IN_STORAGE = 'IN_STORAGE', _('In Storage')
    DECOMMISSIONED = 'DECOMMISSIONED', _('Decommissioned')


class Aircraft(models.Model):
    """
    Represents an aircraft in the fleet for maintenance tracking and flight operations.
    """
    registration_number = models.CharField(
        _('registration number'),
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_('Unique aircraft registration tail number (e.g., N12345, VT-FFX).')
    )
    aircraft_type = models.CharField(
        _('aircraft type'),
        max_length=100,
        db_index=True,
        help_text=_('Category or type (e.g., Commercial Jet, Regional Jet, Turboprop).')
    )
    model = models.CharField(
        _('model'),
        max_length=100,
        db_index=True,
        help_text=_('Specific aircraft model designation (e.g., Boeing 737-800, Airbus A320neo).')
    )
    manufacturer = models.CharField(
        _('manufacturer'),
        max_length=100,
        db_index=True,
        help_text=_('Aircraft manufacturer (e.g., Boeing, Airbus, Bombardier).')
    )
    serial_number = models.CharField(
        _('serial number'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Manufacturer Serial Number (MSN).')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=AircraftStatus.choices,
        default=AircraftStatus.ACTIVE,
        db_index=True
    )
    manufacture_date = models.DateField(
        _('manufacture date'),
        null=True,
        blank=True
    )
    service_entry_date = models.DateField(
        _('service entry date'),
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
        db_table = 'aircraft'
        ordering = ['-created_at']
        verbose_name = _('aircraft')
        verbose_name_plural = _('aircraft')

    def clean(self):
        super().clean()
        if self.registration_number:
            self.registration_number = self.registration_number.strip().upper()
        if self.serial_number:
            self.serial_number = self.serial_number.strip()
        if self.manufacture_date and self.service_entry_date:
            if self.service_entry_date < self.manufacture_date:
                raise ValidationError({
                    'service_entry_date': _('Service entry date cannot be earlier than manufacture date.')
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registration_number} - {self.model} ({self.get_status_display()})"


class Equipment(models.Model):
    """
    Represents an equipment, major component, or subsystem attached to an aircraft or in storage.
    """
    equipment_code = models.CharField(
        _('equipment code'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique internal identifier for the equipment (e.g., EQ-ENG-001).')
    )
    name = models.CharField(
        _('name'),
        max_length=150,
        help_text=_('Descriptive name of the equipment (e.g., CFM56-7B Turbofan Engine).')
    )
    equipment_type = models.CharField(
        _('equipment type'),
        max_length=50,
        choices=EquipmentType.choices,
        default=EquipmentType.OTHER,
        db_index=True
    )
    manufacturer = models.CharField(
        _('manufacturer'),
        max_length=100,
        db_index=True
    )
    serial_number = models.CharField(
        _('serial number'),
        max_length=50,
        blank=True,
        default='',
        db_index=True
    )
    status = models.CharField(
        _('status'),
        max_length=30,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.OPERATIONAL,
        db_index=True
    )
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment',
        verbose_name=_('assigned aircraft'),
        help_text=_('Aircraft currently hosting this equipment (leave blank if in inventory/storage).')
    )
    location = models.CharField(
        _('location'),
        max_length=150,
        blank=True,
        default='',
        help_text=_('Physical location if not installed on an aircraft (e.g., Hangar 1 - Bay B).')
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
        db_table = 'equipment'
        ordering = ['-created_at']
        verbose_name = _('equipment')
        verbose_name_plural = _('equipment')

    def clean(self):
        super().clean()
        if self.equipment_code:
            self.equipment_code = self.equipment_code.strip().upper()
        if self.serial_number:
            self.serial_number = self.serial_number.strip()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.equipment_code} - {self.name} ({self.get_status_display()})"
