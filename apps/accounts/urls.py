"""
URL routes for FlightFix Authentication and User Accounts.
"""

from django.urls import path
from apps.accounts.views import (
    RegisterView,
    LoginView,
    CurrentUserView,
    CustomTokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='auth-refresh'),
    path('me/', CurrentUserView.as_view(), name='auth-me'),
]
