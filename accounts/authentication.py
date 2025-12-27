import json
import logging
from urllib.request import Request, urlopen

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .grouping import DEFAULT_GROUPS, EMPLOYEE_GROUPS, HR_GROUPS, MANAGER_GROUPS, ROLE_TO_BASE_GROUP
from .models import normalize_email_address

logger = logging.getLogger(__name__)

KNOWN_GROUPS = set(DEFAULT_GROUPS)


def _normalize_groups(raw_groups):
    if not raw_groups:
        return []
    if isinstance(raw_groups, str):
        items = [raw_groups]
    else:
        items = list(raw_groups)
    return [item.strip().upper() for item in items if str(item).strip()]


def _infer_role(user_model, role_value, groups, is_superuser):
    if is_superuser:
        return user_model.Role.ADMIN
    if role_value in user_model.Role.values:
        return role_value
    group_set = set(groups)
    if group_set & HR_GROUPS:
        return user_model.Role.HR
    if group_set & MANAGER_GROUPS:
        return user_model.Role.MANAGER
    if group_set & EMPLOYEE_GROUPS:
        return user_model.Role.EMPLOYEE
    return user_model.Role.EMPLOYEE


class HybridJWTAuthentication(BaseAuthentication):
    """Accept external JWTs via JWKS and local SimpleJWT tokens when enabled."""

    def __init__(self):
        self.local_auth = JWTAuthentication()

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if header[0].lower() != b"bearer":
            return None
        if len(header) != 2:
            raise AuthenticationFailed("Invalid authorization header.")

        raw_token = header[1].decode("utf-8")

        if self._is_external_token(raw_token):
            user = self._authenticate_external(raw_token)
            return (user, raw_token)

        if getattr(settings, "AUTH_LOCAL_ENABLED", True):
            return self.local_auth.authenticate(request)

        raise AuthenticationFailed("Local authentication is disabled.")

    def _is_external_token(self, raw_token):
        jwks_url = getattr(settings, "AUTH_JWKS_URL", "")
        if not jwks_url:
            return False

        try:
            headers = jwt.get_unverified_header(raw_token)
        except Exception as exc:  # pragma: no cover - defensive
            raise AuthenticationFailed("Invalid token header.") from exc

        alg = headers.get("alg")
        allowed_algs = [alg.strip() for alg in getattr(settings, "AUTH_JWT_ALGORITHMS", ["RS256"])]
        if alg not in allowed_algs:
            return False

        expected_issuer = getattr(settings, "AUTH_ISSUER", "")
        if expected_issuer:
            try:
                claims = jwt.decode(raw_token, options={"verify_signature": False})
            except Exception as exc:  # pragma: no cover - defensive
                raise AuthenticationFailed("Invalid token claims.") from exc
            if claims.get("iss") != expected_issuer:
                raise AuthenticationFailed("Token issuer mismatch.")

        return True

    def _authenticate_external(self, raw_token):
        claims = self._decode_external_token(raw_token)
        user = self._sync_shadow_user(claims, raw_token)
        return user

    def _decode_external_token(self, raw_token):
        key = self._get_public_key(raw_token)
        algorithms = [alg.strip() for alg in getattr(settings, "AUTH_JWT_ALGORITHMS", ["RS256"])]
        issuer = getattr(settings, "AUTH_ISSUER", "")
        audience = getattr(settings, "AUTH_AUDIENCE", "")
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": bool(issuer),
            "verify_aud": bool(audience),
        }

        kwargs = {"key": key, "algorithms": algorithms, "options": options}
        if issuer:
            kwargs["issuer"] = issuer
        if audience:
            kwargs["audience"] = audience

        try:
            return jwt.decode(raw_token, **kwargs)
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationFailed("Token expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationFailed("Invalid token.") from exc

    def _get_public_key(self, raw_token):
        headers = jwt.get_unverified_header(raw_token)
        kid = headers.get("kid")

        keys = self._get_jwks(force_refresh=False)
        key = self._find_key(keys, kid)
        if not key:
            keys = self._get_jwks(force_refresh=True)
            key = self._find_key(keys, kid)
        if not key:
            raise AuthenticationFailed("Signing key not found.")

        if not str(headers.get("alg", "")).startswith("RS"):
            raise AuthenticationFailed("Unsupported JWT algorithm.")

        return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))

    def _get_jwks(self, *, force_refresh):
        jwks_url = getattr(settings, "AUTH_JWKS_URL", "")
        if not jwks_url:
            raise AuthenticationFailed("External authentication not configured.")

        cache_key = "auth:jwks"
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                return cached

        try:
            request = Request(jwks_url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=5) as response:
                payload = json.load(response)
        except Exception as exc:
            raise AuthenticationFailed("Unable to fetch JWKS.") from exc

        keys = payload.get("keys", payload)
        if not keys:
            raise AuthenticationFailed("Invalid JWKS payload.")

        cache.set(cache_key, keys, timeout=getattr(settings, "AUTH_JWKS_CACHE_SECONDS", 3600))
        return keys

    @staticmethod
    def _find_key(keys, kid):
        if not isinstance(keys, list):
            return None
        if kid:
            for key in keys:
                if key.get("kid") == kid:
                    return key
            return None
        return keys[0] if len(keys) == 1 else None

    def _sync_shadow_user(self, claims, raw_token):
        user_model = get_user_model()

        external_id = claims.get("user_id") or claims.get("sub")
        external_id = str(external_id) if external_id is not None else None

        payload = self._merge_user_payload(claims, raw_token, external_id)

        email = payload.get("email")
        if not email:
            raise AuthenticationFailed("Email claim required.")

        email = normalize_email_address(email)
        username = payload.get("username") or email
        groups = _normalize_groups(payload.get("groups"))

        role = _infer_role(
            user_model,
            payload.get("role"),
            groups,
            bool(payload.get("is_superuser")),
        )

        user = self._get_or_create_user(
            user_model,
            external_id=external_id,
            email=email,
            username=username,
        )

        user.email = email
        user.username = username
        user.role = role
        user.is_active = True
        if payload.get("is_staff") is not None:
            user.is_staff = bool(payload.get("is_staff"))
        if payload.get("is_superuser") is not None:
            user.is_superuser = bool(payload.get("is_superuser"))
        if external_id:
            user.external_auth_id = external_id

        email_verified_at = payload.get("email_verified_at")
        if email_verified_at and not user.email_verified_at:
            user.is_email_verified = True
            user.email_verified_at = email_verified_at

        user.save()
        self._sync_groups(user, role, groups)
        return user

    def _merge_user_payload(self, claims, raw_token, external_id):
        payload = dict(claims)
        if not payload.get("email") or not payload.get("role") or not payload.get("groups"):
            userinfo = self._fetch_userinfo(raw_token, external_id)
            for key in ("email", "username", "role", "groups", "is_staff", "is_superuser", "email_verified_at"):
                if not payload.get(key) and userinfo.get(key) is not None:
                    payload[key] = userinfo.get(key)
        return payload

    def _fetch_userinfo(self, raw_token, external_id):
        url = getattr(settings, "AUTH_USERINFO_URL", "")
        if not url:
            return {}

        cache_key = f"auth:userinfo:{external_id}" if external_id else None
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return cached

        try:
            request = Request(
                url,
                headers={
                    "Authorization": f"Bearer {raw_token}",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=5) as response:
                payload = json.load(response)
        except Exception as exc:
            logger.warning("Failed to fetch auth userinfo: %s", exc)
            return {}

        data = payload.get("data", payload)
        if cache_key:
            cache.set(cache_key, data, timeout=getattr(settings, "AUTH_USERINFO_CACHE_SECONDS", 300))
        return data

    def _get_or_create_user(self, user_model, *, external_id, email, username):
        user = None
        if external_id:
            user = user_model.objects.filter(external_auth_id=external_id).first()
        if not user:
            user = user_model.objects.filter(email__iexact=email).first()
        if not user and username:
            user = user_model.objects.filter(username__iexact=username).first()
        if user:
            return user
        return user_model.objects.create_user(email=email, password=None, username=username)

    def _sync_groups(self, user, role, groups):
        group_names = set(groups)
        base_group = ROLE_TO_BASE_GROUP.get(role)
        if base_group:
            group_names.add(base_group)

        target_names = group_names & KNOWN_GROUPS
        if not target_names:
            user.groups.clear()
            return

        group_objs = []
        for name in sorted(target_names):
            group, _ = Group.objects.get_or_create(name=name)
            group_objs.append(group)

        user.groups.set(group_objs)
