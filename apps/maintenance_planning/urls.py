"""
URL routes for FlightFix Maintenance Planning & Scheduling module.
"""

from rest_framework.routers import DefaultRouter
from apps.maintenance_planning.views import (
    MaintenanceScheduleViewSet,
    MaintenanceTaskViewSet,
)

router = DefaultRouter()
router.register('schedules', MaintenanceScheduleViewSet, basename='maintenance-schedules')
router.register('tasks', MaintenanceTaskViewSet, basename='maintenance-tasks')

urlpatterns = router.urls
