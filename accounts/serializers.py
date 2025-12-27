from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import normalize_email_address

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    """Minimal user payload for auth responses."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_email_verified",
            "email_verified_at",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """Register a new user with email + username + password."""

    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField()

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "password"]

    def validate_email(self, value):
        normalized = normalize_email_address(value)
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe deja.")
        return normalized

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError("Le username est requis.")
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Un utilisateur avec ce username existe deja.")
        return username

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            role=User.Role.EMPLOYEE,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user
