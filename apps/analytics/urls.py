"""
URL routing for FlightFix Analytics & Reporting module.
"""

from django.urls import path
from apps.analytics.views import (
    AircraftSummaryView,
    AnalyticsDashboardView,
    ComplianceSummaryView,
    InventorySummaryView,
    MaintenanceSummaryView,
    SupplyChainSummaryView,
    TechnicianPerformanceView,
)

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('maintenance-summary/', MaintenanceSummaryView.as_view(), name='maintenance-summary'),
    path('aircraft-summary/', AircraftSummaryView.as_view(), name='aircraft-summary'),
    path('inventory-summary/', InventorySummaryView.as_view(), name='inventory-summary'),
    path('compliance-summary/', ComplianceSummaryView.as_view(), name='compliance-summary'),
    path('supply-chain-summary/', SupplyChainSummaryView.as_view(), name='supply-chain-summary'),
    path('technician-performance/', TechnicianPerformanceView.as_view(), name='technician-performance'),
]
