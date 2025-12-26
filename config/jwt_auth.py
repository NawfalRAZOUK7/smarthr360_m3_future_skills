"""JWT Authentication Configuration and Views.

This module provides JWT (JSON Web Token) authentication for the SmartHR360 API.
Uses djangorestframework-simplejwt with enhanced security features.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

logger = logging.getLogger(__name__)
User = get_user_model()


# JWT Settings Configuration (add to settings/base.py)
JWT_SETTINGS = {
    # Token Lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Rotation & Blacklist
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # Security
    "ALGORITHM": "HS256",
    "SIGNING_KEY": None,  # Uses SECRET_KEY if not set
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": "smarthr360",
    # Token Claims
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    # Token Behavior
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    # Sliding Tokens (if using sliding instead of refresh)
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=30),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=7),
    # Additional Claims
    "JTI_CLAIM": "jti",  # JWT ID for token tracking
}


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that adds additional user information to the token response."""

    @classmethod
    def get_token(cls, user):
        """Generate JWT token with custom user claims.

        Extends the base token with username, email, staff status,
        user groups, and issuance timestamp.
        """
        token = super().get_token(user)

        # Add custom claims
        token["username"] = user.username
        token["email"] = user.email if hasattr(user, "email") else ""
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser

        # Add role/group information
        if hasattr(user, "groups"):
            token["groups"] = list(user.groups.values_list("name", flat=True))

        # Add timestamp
        token["issued_at"] = timezone.now().isoformat()

        return token

    def validate(self, attrs):
        """Validate the token and add user information to the response."""
        data = super().validate(attrs)

        # Add extra responses data
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email if hasattr(self.user, "email") else "",
            "is_staff": self.user.is_staff,
            "is_superuser": self.user.is_superuser,
            "groups": (list(self.user.groups.values_list("name", flat=True)) if hasattr(self.user, "groups") else []),
        }

        # Log successful login
        logger.info(
            f"JWT token issued for user: {self.user.username} (ID: {self.user.id})",
            extra={
                "user_id": self.user.id,
                "username": self.user.username,
                "event": "jwt_token_issued",
            },
        )

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view with additional logging and security checks."""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """Handle POST request for token obtain with logging."""
        # Log login attempt
        username = request.data.get("username", "unknown")
        logger.info(
            f"JWT login attempt for username: {username}",
            extra={
                "username": username,
                "ip_address": self.get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "event": "jwt_login_attempt",
            },
        )

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            logger.info(
                f"JWT login successful for username: {username}",
                extra={
                    "username": username,
                    "event": "jwt_login_success",
                },
            )
        else:
            logger.warning(
                f"JWT login failed for username: {username}",
                extra={
                    "username": username,
                    "event": "jwt_login_failed",
                },
            )

        return response

    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view with logging."""

    def post(self, request, *args, **kwargs):
        """Handle POST request for token refresh with logging."""
        logger.debug(
            "JWT token refresh attempt",
            extra={
                "ip_address": CustomTokenObtainPairView.get_client_ip(request),
                "event": "jwt_token_refresh",
            },
        )

        return super().post(request, *args, **kwargs)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint that blacklists the user's refresh token.

    Requires the refresh token in the request body.
    """
    try:
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        logger.info(
            f"JWT token blacklisted for user: {request.user.username}",
            extra={
                "user_id": request.user.id,
                "username": request.user.username,
                "event": "jwt_logout",
            },
        )

        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(
            f"JWT logout failed: {str(e)}",
            extra={
                "user_id": request.user.id,
                "username": request.user.username,
                "error": str(e),
                "event": "jwt_logout_failed",
            },
        )
        return Response(
            {"error": "Invalid token or token already blacklisted"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_token_view(request):
    """Endpoint to verify if the current token is valid."""
    return Response(
        {
            "valid": True,
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email if hasattr(request.user, "email") else "",
            },
        },
        status=status.HTTP_200_OK,
    )


# Example usage in views:
# from rest_framework.permissions import IsAuthenticated
# from rest_framework_simplejwt.authentication import JWTAuthentication
#
# class MyAPIView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         # Access authenticated user via request.user
#         return Response({'user': request.user.username})
