"""
User model for FlightFix accounts application.
"""

import re
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """
    Validates standard international/national phone number formats.
    Allows 7 to 20 digits with optional leading + and common separators.
    """
    if value:
        pattern = r'^\+?[0-9\s\-\(\)]{7,20}$'
        if not re.match(pattern, value):
            raise ValidationError(
                _('Enter a valid phone number (7-20 digits, optional leading +).')
            )


class CustomUserManager(UserManager):
    """
    Custom user manager supporting email normalization and default role assignment.
    """

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.FIELD_TECHNICIAN)
        return super().create_user(username, email=email, password=password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    """
    FlightFix custom user model supporting Role-Based Access Control (RBAC).
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        SAFETY_OFFICER = 'SAFETY_OFFICER', _('Safety Officer')
        CONTRACTS_MANAGER = 'CONTRACTS_MANAGER', _('Contracts Manager')
        FIELD_TECHNICIAN = 'FIELD_TECHNICIAN', _('Field Technician')

    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    phone = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        default='',
        validators=[validate_phone_number],
    )
    role = models.CharField(
        _('role'),
        max_length=30,
        choices=Role.choices,
        default=Role.FIELD_TECHNICIAN,
        db_index=True,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    objects = CustomUserManager()

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        db_table = 'accounts_user'
        ordering = ['-created_at']
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_safety_officer_role(self):
        return self.role == self.Role.SAFETY_OFFICER

    @property
    def is_contracts_manager_role(self):
        return self.role == self.Role.CONTRACTS_MANAGER

    @property
    def is_field_technician_role(self):
        return self.role == self.Role.FIELD_TECHNICIAN
