"""
Serializers for FlightFix User Management and Authentication.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, validate_phone_number


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for public User profile representation.
    """
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'role',
            'is_active',
            'is_staff',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'is_active',
            'is_staff',
            'created_at',
            'updated_at',
        )


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with field and password validation.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text=_('Minimum 8 characters, meeting standard security requirements.')
    )
    email = serializers.EmailField(
        required=True,
        help_text=_('Valid email address (must be unique).')
    )
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=20
    )
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        default=User.Role.FIELD_TECHNICIAN,
        required=False
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'phone',
            'role',
        )

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_('Username cannot be blank.'))
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(_('A user with this username already exists.'))
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError(_('Email cannot be blank.'))
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_('A user with this email already exists.'))
        return value

    def validate_phone(self, value):
        if value:
            try:
                validate_phone_number(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(list(exc.messages))
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                _('Password must contain at least 8 characters.')
            )
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login supporting username or email with password.
    Returns JWT access and refresh tokens, user profile, and user role.
    """
    username = serializers.CharField(
        required=True,
        help_text=_('Username or email address.')
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username_or_email = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        if not username_or_email or not password:
            raise serializers.ValidationError(
                _('Both username/email and password are required.')
            )

        # Allow user to log in with either username or email
        user = None
        if '@' in username_or_email:
            try:
                user_obj = User.objects.get(email__iexact=username_or_email)
                username_to_auth = user_obj.username
            except User.DoesNotExist:
                username_to_auth = None
        else:
            username_to_auth = username_or_email

        if username_to_auth:
            user = authenticate(username=username_to_auth, password=password)

        if not user:
            raise serializers.ValidationError(
                _('Invalid credentials. Please verify your username/email and password.')
            )

        if not user.is_active:
            raise serializers.ValidationError(
                _('This user account is inactive. Please contact an administrator.')
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        # Include role in token claims
        refresh['role'] = user.role
        refresh['username'] = user.username

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'role': user.role,
        }
