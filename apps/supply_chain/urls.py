"""
URL configuration for FlightFix ERP & Supply Chain Integration module.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.supply_chain.views import (
    SupplierViewSet,
    PurchaseOrderViewSet,
    PurchaseOrderItemViewSet,
)

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='suppliers')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-orders')
router.register(r'purchase-order-items', PurchaseOrderItemViewSet, basename='purchase-order-items')

urlpatterns = [
    path('', include(router.urls)),
]
