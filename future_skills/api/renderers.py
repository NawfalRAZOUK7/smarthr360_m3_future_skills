"""Custom renderers for versioned Accept headers and response envelopes."""

from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    """Optional response envelope to align with auth APIs.

    Enable with header `X-Response-Envelope: 1` or query `?envelope=1`.
    Defaults to raw DRF payloads for backward compatibility.
    """

    envelope_header = "X-Response-Envelope"
    envelope_query_param = "envelope"
    truthy_values = {"1", "true", "yes", "on"}

    def _should_envelope(self, request) -> bool:
        if not request:
            return False

        header_value = ""
        try:
            header_value = request.headers.get(self.envelope_header, "")
        except Exception:  # pragma: no cover - defensive
            header_value = request.META.get("HTTP_X_RESPONSE_ENVELOPE", "")

        if isinstance(header_value, str) and header_value.lower() in self.truthy_values:
            return True

        try:
            query_value = request.query_params.get(self.envelope_query_param, "")
        except Exception:  # pragma: no cover - defensive
            query_value = ""

        return isinstance(query_value, str) and query_value.lower() in self.truthy_values

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        request = renderer_context.get("request") if renderer_context else None

        if response and 200 <= response.status_code < 300 and isinstance(data, (dict, list)):
            if isinstance(data, dict) and "data" in data and "meta" in data:
                return super().render(data, accepted_media_type, renderer_context)
            if self._should_envelope(request):
                payload = {"data": data, "meta": {"success": True}}
                return super().render(payload, accepted_media_type, renderer_context)

        return super().render(data, accepted_media_type, renderer_context)


class VendorV1JSONRenderer(EnvelopeJSONRenderer):
    media_type = "application/vnd.smarthr360.v1+json"
    format = "json"


class VendorV2JSONRenderer(EnvelopeJSONRenderer):
    media_type = "application/vnd.smarthr360.v2+json"
    format = "json"
