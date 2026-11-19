"""
URL routes for FlightFix Aircraft and Equipment APIs.
"""

from rest_framework.routers import DefaultRouter
from apps.aircraft.views import AircraftViewSet, EquipmentViewSet

router = DefaultRouter()
router.register('aircraft', AircraftViewSet, basename='aircraft')
router.register('equipment', EquipmentViewSet, basename='equipment')

urlpatterns = router.urls
