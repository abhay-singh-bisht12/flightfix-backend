"""
URL configuration for FlightFix Maintenance Execution & Documentation module.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.maintenance_execution.views import (
    MaintenanceExecutionViewSet,
    MaintenanceDocumentationViewSet,
)

router = DefaultRouter()
router.register(r'records', MaintenanceExecutionViewSet, basename='maintenance-execution-records')
router.register(r'documentation', MaintenanceDocumentationViewSet, basename='maintenance-documentation')

urlpatterns = [
    path('', include(router.urls)),
]
