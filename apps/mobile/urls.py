"""
URL routing for FlightFix Mobile / Field Technician Support module.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.mobile.views import (
    TechnicianAircraftViewSet,
    TechnicianAvailablePartsViewSet,
    TechnicianComplianceViewSet,
    TechnicianDashboardView,
    TechnicianExecutionViewSet,
    TechnicianTaskViewSet,
    TechnicianWorkOrderViewSet,
)

app_name = 'mobile'

router = DefaultRouter()
router.register('my-tasks', TechnicianTaskViewSet, basename='my-tasks')
router.register('my-work-orders', TechnicianWorkOrderViewSet, basename='my-work-orders')
router.register('my-executions', TechnicianExecutionViewSet, basename='my-executions')
router.register('my-aircraft', TechnicianAircraftViewSet, basename='my-aircraft')
router.register('my-compliance', TechnicianComplianceViewSet, basename='my-compliance')
router.register('available-parts', TechnicianAvailablePartsViewSet, basename='available-parts')

urlpatterns = [
    path('dashboard/', TechnicianDashboardView.as_view(), name='technician-dashboard'),
    path('', include(router.urls)),
]
