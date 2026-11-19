"""
Views for FlightFix User Authentication and Profile Management.
"""

from rest_framework import status, generics, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Registers a new FlightFix user and generates initial JWT tokens.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens upon successful registration
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['username'] = user.username

        response_data = {
            'status': 'success',
            'message': 'User registered successfully.',
            'user': UserSerializer(user).data,
            'role': user.role,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    """
    POST /api/auth/login/
    Authenticates user credentials and returns JWT tokens with user profile.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class CurrentUserView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/
    Returns the profile and role of the currently authenticated user.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/auth/refresh/
    Takes a valid refresh token and returns a new access token.
    """
    pass
