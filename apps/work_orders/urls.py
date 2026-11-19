"""
URL routes for FlightFix Work Order Management.
"""

from rest_framework.routers import DefaultRouter
from apps.work_orders.views import WorkOrderViewSet

router = DefaultRouter()
router.register('', WorkOrderViewSet, basename='work-orders')

urlpatterns = router.urls
