"""
API Versioning System

Provides flexible API versioning through URL path and Accept header negotiation.
Supports multiple API versions with deprecation warnings and backward compatibility.
"""

import warnings

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotAcceptable
from rest_framework.versioning import AcceptHeaderVersioning, NamespaceVersioning


class URLPathVersioning(NamespaceVersioning):
    """
    Version API through URL path namespacing (e.g., /api/v1/, /api/v2/).

    Example URLs:
        /api/v1/future-skills/
        /api/v2/future-skills/

    This is the primary versioning method as it's explicit and cache-friendly.
    """

    default_version = "v1"
    allowed_versions = ["v1", "v2"]
    version_param = "version"

    def determine_version(self, request, *args, **kwargs):
        """
        Determine API version from URL namespace.
        Falls back to default_version if not specified.
        """
        version = super().determine_version(request, *args, **kwargs)

        if version is None:
            version = self.default_version

        # Check for deprecated versions
        if version == "v1":
            self._add_deprecation_warning(request, version)

        return version

    def _add_deprecation_warning(self, request, version):
        """Add deprecation warning to response headers"""
        if not hasattr(request, "_deprecation_warning"):
            request._deprecation_warning = (
                f"API version {version} is deprecated. "
                f"Please migrate to v2. "
                f"v1 will be sunset on 2026-06-01."
            )


class CustomAcceptHeaderVersioning(AcceptHeaderVersioning):
    """
    Version API through Accept header (e.g., Accept: application/json; version=v1).

    Example header:
        Accept: application/vnd.smarthr360.v1+json
        Accept: application/vnd.smarthr360.v2+json

    This is an alternative method for clients that prefer header-based versioning.
    """

    default_version = "v1"
    allowed_versions = ["v1", "v2"]
    version_param = "version"

    def determine_version(self, request, *args, **kwargs):
        """
        Determine API version from Accept header.
        Supports vendor-specific media types.
        """
        media_type = request.accepted_media_type
        version = self.default_version

        if media_type and "vnd.smarthr360" in media_type:
            # Extract version from vendor media type
            # e.g., application/vnd.smarthr360.v1+json -> v1
            parts = media_type.split(".")
            for part in parts:
                if part.startswith("v") and part[1:].isdigit():
                    version = part
                    break

        if version not in self.allowed_versions:
            raise NotAcceptable(
                _("Invalid version in Accept header. Allowed versions: {}").format(
                    ", ".join(self.allowed_versions)
                )
            )

        # Check for deprecated versions
        if version == "v1":
            self._add_deprecation_warning(request, version)

        return version

    def _add_deprecation_warning(self, request, version):
        """Add deprecation warning to response headers"""
        if not hasattr(request, "_deprecation_warning"):
            request._deprecation_warning = (
                f"API version {version} is deprecated. "
                f"Please migrate to v2. "
                f"v1 will be sunset on 2026-06-01."
            )


class QueryParameterVersioning:
    """
    Version API through query parameter (e.g., ?version=v1).

    Example URL:
        /api/future-skills/?version=v1

    Note: This method is NOT recommended for production as it's not cache-friendly
    and can cause issues with URL-based caching strategies. Use URL path versioning instead.

    This is provided for backward compatibility or special use cases only.
    """

    default_version = "v1"
    allowed_versions = ["v1", "v2"]
    version_param = "version"

    def determine_version(self, request, *args, **kwargs):
        """Determine API version from query parameter"""
        version = request.query_params.get(self.version_param, self.default_version)

        if version not in self.allowed_versions:
            raise NotAcceptable(
                _("Invalid version parameter. Allowed versions: {}").format(
                    ", ".join(self.allowed_versions)
                )
            )

        # Warn about query parameter versioning
        warnings.warn(
            "Query parameter versioning is not recommended. "
            "Consider using URL path versioning instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return version


# Versioning strategy configuration
# Default: URL path versioning (most explicit and cache-friendly)
DEFAULT_VERSIONING_CLASS = URLPathVersioning

# Alternative: Accept header versioning (for clients that prefer headers)
ALTERNATIVE_VERSIONING_CLASS = CustomAcceptHeaderVersioning


def get_api_version(request):
    """
    Utility function to get the current API version from request.

    Args:
        request: Django request object

    Returns:
        str: API version (e.g., 'v1', 'v2')
    """
    return getattr(request, "version", "v1")


def is_deprecated_version(version):
    """
    Check if an API version is deprecated.

    Args:
        version: API version string (e.g., 'v1')

    Returns:
        bool: True if version is deprecated
    """
    deprecated_versions = ["v1"]  # v1 is deprecated
    return version in deprecated_versions


def get_version_info():
    """
    Get information about all API versions.

    Returns:
        dict: Version information including status, sunset dates, etc.
    """
    return {
        "current": "v2",
        "supported": ["v1", "v2"],
        "deprecated": ["v1"],
        "versions": {
            "v1": {
                "status": "deprecated",
                "released": "2024-01-01",
                "deprecated_date": "2025-12-01",
                "sunset_date": "2026-06-01",
                "documentation": "/api/docs/?version=v1",
            },
            "v2": {
                "status": "current",
                "released": "2025-01-01",
                "deprecated_date": None,
                "sunset_date": None,
                "documentation": "/api/docs/?version=v2",
                "changes": [
                    "Enhanced pagination with cursor support",
                    "Improved error responses with detailed codes",
                    "Added bulk operations optimization",
                    "Consistent datetime formatting (ISO 8601)",
                    "Enhanced filtering and search capabilities",
                ],
            },
        },
    }
