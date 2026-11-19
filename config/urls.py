"""
URL configuration for FlightFix project.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint to verify backend service status.
    """
    return Response(
        {
            "status": "success",
            "message": "FlightFix backend is running"
        },
        status=status.HTTP_200_OK
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.aircraft.urls')),
    path('api/maintenance/', include('apps.maintenance_planning.urls')),
    path('api/work-orders/', include('apps.work_orders.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/maintenance-execution/', include('apps.maintenance_execution.urls')),
    path('api/compliance/', include('apps.compliance.urls')),
    path('api/supply-chain/', include('apps.supply_chain.urls')),
    path('api/mobile/', include('apps.mobile.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
]
