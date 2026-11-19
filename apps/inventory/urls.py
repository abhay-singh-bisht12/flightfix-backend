"""
URL configuration for FlightFix Spare Parts Inventory module.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.inventory.views import SparePartViewSet, InventoryTransactionViewSet

router = DefaultRouter()
router.register(r'parts', SparePartViewSet, basename='spare-parts')
router.register(r'transactions', InventoryTransactionViewSet, basename='inventory-transactions')

urlpatterns = [
    path('', include(router.urls)),
]
