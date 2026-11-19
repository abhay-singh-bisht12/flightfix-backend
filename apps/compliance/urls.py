"""
URL configuration for FlightFix Airworthiness & Regulatory Compliance module.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.compliance.views import (
    ComplianceRequirementViewSet,
    ComplianceRecordViewSet,
)

router = DefaultRouter()
router.register(r'requirements', ComplianceRequirementViewSet, basename='compliance-requirements')
router.register(r'records', ComplianceRecordViewSet, basename='compliance-records')

urlpatterns = [
    path('', include(router.urls)),
]
