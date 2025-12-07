"""Custom renderers for vendor-specific Accept headers."""

from rest_framework.renderers import JSONRenderer


class VendorV1JSONRenderer(JSONRenderer):
    media_type = "application/vnd.smarthr360.v1+json"
    format = "json"


class VendorV2JSONRenderer(JSONRenderer):
    media_type = "application/vnd.smarthr360.v2+json"
    format = "json"
