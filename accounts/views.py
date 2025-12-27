from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserPublicSerializer


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        if not getattr(settings, "AUTH_LOCAL_ENABLED", True):
            return Response(
                {"detail": "Local authentication is disabled."},
                status=status.HTTP_410_GONE,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        payload = {
            "user": UserPublicSerializer(user).data,
            "tokens": get_tokens_for_user(user),
        }
        return Response(payload, status=status.HTTP_201_CREATED)
