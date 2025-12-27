import json
from unittest import mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from accounts.authentication import HybridJWTAuthentication
from accounts.models import User


class HybridJWTAuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = cls.private_key.public_key()
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
        jwk["kid"] = "test-key"
        cls.jwks = [jwk]

    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth = HybridJWTAuthentication()

    def _make_token(self, payload):
        return jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": "test-key"})

    @override_settings(
        AUTH_JWKS_URL="https://auth.local/.well-known/jwks.json",
        AUTH_ISSUER="auth-service",
        AUTH_JWT_ALGORITHMS=["RS256"],
        AUTH_LOCAL_ENABLED=False,
    )
    def test_external_auth_creates_shadow_user(self):
        payload = {
            "iss": "auth-service",
            "user_id": 42,
            "email": "hr_admin@example.com",
            "username": "hr_admin",
            "role": "HR",
            "groups": ["HR_ADMIN"],
        }
        token = self._make_token(payload)
        request = self.factory.get(
            "/api/v2/predictions/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        with mock.patch.object(HybridJWTAuthentication, "_get_jwks", return_value=self.jwks):
            user, _ = self.auth.authenticate(request)

        self.assertEqual(user.email, "hr_admin@example.com")
        self.assertEqual(user.external_auth_id, "42")
        self.assertEqual(user.role, User.Role.HR)
        self.assertTrue(
            user.groups.filter(name="HR").exists(),
        )
        self.assertTrue(
            user.groups.filter(name="HR_ADMIN").exists(),
        )

    @override_settings(
        AUTH_JWKS_URL="https://auth.local/.well-known/jwks.json",
        AUTH_ISSUER="auth-service",
        AUTH_USERINFO_URL="https://auth.local/api/auth/me/",
        AUTH_JWT_ALGORITHMS=["RS256"],
        AUTH_LOCAL_ENABLED=False,
    )
    def test_external_auth_fetches_userinfo_for_role(self):
        payload = {
            "iss": "auth-service",
            "user_id": 7,
            "email": "manager@example.com",
        }
        token = self._make_token(payload)
        request = self.factory.get(
            "/api/v2/predictions/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        with mock.patch.object(HybridJWTAuthentication, "_get_jwks", return_value=self.jwks):
            with mock.patch.object(
                HybridJWTAuthentication,
                "_fetch_userinfo",
                return_value={"role": "MANAGER", "username": "manager"},
            ):
                user, _ = self.auth.authenticate(request)

        self.assertEqual(user.role, User.Role.MANAGER)
        self.assertEqual(user.username, "manager")

    @override_settings(
        AUTH_JWT_SHARED_SECRET="shared-secret",
        AUTH_ISSUER="smarthr360",
        AUTH_JWT_ALGORITHMS=["HS256"],
        AUTH_LOCAL_ENABLED=False,
    )
    def test_external_auth_shared_secret_hs256(self):
        payload = {
            "iss": "smarthr360",
            "user_id": 99,
            "email": "employee@example.com",
            "role": "EMPLOYEE",
        }
        token = jwt.encode(payload, "shared-secret", algorithm="HS256")
        request = self.factory.get(
            "/api/v2/predictions/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        user, _ = self.auth.authenticate(request)

        self.assertEqual(user.email, "employee@example.com")
        self.assertEqual(user.external_auth_id, "99")
        self.assertEqual(user.role, User.Role.EMPLOYEE)
