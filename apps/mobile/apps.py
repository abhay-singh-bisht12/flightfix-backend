"""
Application configuration for FlightFix Mobile / Field Technician Support module.
"""

from django.apps import AppConfig


class MobileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mobile'
    verbose_name = 'Mobile / Field Technician Support'
