"""
Application Performance Monitoring (APM) Configuration
SmartHR360 Future Skills Platform

Integrates Elastic APM and Sentry for comprehensive application monitoring,
error tracking, and performance analysis.
"""

import os
from typing import Any, Dict, Optional


# ============================================================================
# ELASTIC APM CONFIGURATION
# ============================================================================


def get_elastic_apm_config() -> Optional[Dict[str, Any]]:
    """
    Get Elastic APM configuration.

    Returns:
        Dict with Elastic APM settings or None if not configured
    """
    if not os.getenv("ELASTIC_APM_SERVER_URL"):
        return None

    return {
        "SERVICE_NAME": os.getenv(
            "ELASTIC_APM_SERVICE_NAME", "smarthr360-future-skills"
        ),
        "SECRET_TOKEN": os.getenv("ELASTIC_APM_SECRET_TOKEN", ""),
        "SERVER_URL": os.getenv("ELASTIC_APM_SERVER_URL"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
        "DEBUG": os.getenv("ELASTIC_APM_DEBUG", "false").lower() == "true",
        # Transaction settings
        "TRANSACTION_SAMPLE_RATE": float(
            os.getenv("ELASTIC_APM_TRANSACTION_SAMPLE_RATE", "1.0")
        ),
        "TRANSACTION_MAX_SPANS": int(
            os.getenv("ELASTIC_APM_TRANSACTION_MAX_SPANS", "500")
        ),
        # Performance monitoring
        "CAPTURE_BODY": os.getenv(
            "ELASTIC_APM_CAPTURE_BODY", "errors"
        ),  # 'off', 'errors', 'transactions', 'all'
        "CAPTURE_HEADERS": os.getenv("ELASTIC_APM_CAPTURE_HEADERS", "true").lower()
        == "true",
        # Distributed tracing
        "DISTRIBUTED_TRACING": True,
        "TRACE_CONTINUATION_STRATEGY": "continue",
        # Django specific
        "DJANGO_TRANSACTION_NAME_FROM_ROUTE": True,
        "TRANSACTIONS_IGNORE_PATTERNS": [
            "^OPTIONS",
            "healthcheck",
            "readiness",
            "liveness",
        ],
        # Error filtering
        "FILTER_EXCEPTION_TYPES": [
            "Http404",
            "PermissionDenied",
        ],
        # Custom context
        "CUSTOM_CONTEXT_PROCESSORS": [
            "config.apm_config.add_custom_context",
        ],
    }


def add_custom_context(client: Any, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add custom context to APM events.

    Args:
        client: APM client instance
        event_dict: Event dictionary

    Returns:
        Modified event dictionary
    """
    # Add custom tags
    event_dict["tags"] = event_dict.get("tags", {})
    event_dict["tags"]["app"] = "smarthr360"
    event_dict["tags"]["component"] = "future-skills"

    # Add custom metadata
    event_dict["custom"] = event_dict.get("custom", {})
    event_dict["custom"]["environment"] = os.getenv("ENVIRONMENT", "development")

    return event_dict


# ============================================================================
# SENTRY CONFIGURATION
# ============================================================================


def get_sentry_config() -> Optional[Dict[str, Any]]:
    """
    Get Sentry configuration.

    Returns:
        Dict with Sentry settings or None if not configured
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return None

    return {
        "dsn": dsn,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "release": os.getenv("APP_VERSION", "unknown"),
        # Performance monitoring
        "traces_sample_rate": float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        "profiles_sample_rate": float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "1.0")),
        # Error sampling
        "sample_rate": float(os.getenv("SENTRY_SAMPLE_RATE", "1.0")),
        # Integrations
        "integrations": get_sentry_integrations(),
        # Request data
        "send_default_pii": False,
        "max_breadcrumbs": 50,
        "attach_stacktrace": True,
        # Performance
        "max_request_body_size": "medium",  # 'never', 'small', 'medium', 'always'
        # Error filtering
        "ignore_errors": [
            "Http404",
            "PermissionDenied",
            "NotAuthenticated",
            "AuthenticationFailed",
        ],
        # Before send hook
        "before_send": before_send_sentry,
        "before_send_transaction": before_send_transaction,
    }


def get_sentry_integrations() -> list:
    """Get Sentry integrations."""
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    integrations = [
        DjangoIntegration(
            transaction_style="url",
            middleware_spans=True,
            signals_spans=True,
            cache_spans=True,
        ),
        CeleryIntegration(
            monitor_beat_tasks=True,
            exclude_beat_tasks=[],
        ),
        RedisIntegration(),
        LoggingIntegration(
            level=None,  # Capture all logs
            event_level=None,  # Send errors as events
        ),
    ]

    return integrations


def before_send_sentry(
    event: Dict[str, Any], hint: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Process events before sending to Sentry.

    Args:
        event: Event dictionary
        hint: Hint dictionary with additional context

    Returns:
        Modified event or None to drop the event
    """
    # Remove sensitive data
    if "request" in event:
        headers = event["request"].get("headers", {})
        for sensitive_header in ["Authorization", "Cookie", "X-API-Key"]:
            if sensitive_header in headers:
                headers[sensitive_header] = "[Filtered]"

    # Add custom tags
    event.setdefault("tags", {})
    event["tags"]["app"] = "smarthr360"
    event["tags"]["component"] = "future-skills"

    # Add user context if available
    if "user" not in event and hasattr(hint.get("request"), "user"):
        user = hint["request"].user
        if user.is_authenticated:
            event["user"] = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }

    return event


def before_send_transaction(
    event: Dict[str, Any], hint: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Process transactions before sending to Sentry.

    Args:
        event: Event dictionary
        hint: Hint dictionary with additional context

    Returns:
        Modified event or None to drop the transaction
    """
    # Skip health check transactions
    if event.get("transaction") in ["/health/", "/healthcheck/", "/ready/", "/alive/"]:
        return None

    # Add custom tags
    event.setdefault("tags", {})
    event["tags"]["app"] = "smarthr360"
    event["tags"]["component"] = "future-skills"

    return event


# ============================================================================
# APM INITIALIZATION
# ============================================================================


def initialize_apm() -> None:
    """
    Initialize APM tools (Elastic APM and Sentry).
    Should be called during application startup.
    """
    # Initialize Elastic APM
    elastic_config = get_elastic_apm_config()
    if elastic_config:
        try:
            pass

            # Elastic APM is configured via Django settings
            # No need to initialize here, just log
            from config.logging_config import get_logger

            logger = get_logger(__name__)
            logger.info(
                "elastic_apm_configured",
                service_name=elastic_config["SERVICE_NAME"],
                environment=elastic_config["ENVIRONMENT"],
            )
        except ImportError:
            pass

    # Initialize Sentry
    sentry_config = get_sentry_config()
    if sentry_config:
        try:
            import sentry_sdk

            sentry_sdk.init(**sentry_config)

            from config.logging_config import get_logger

            logger = get_logger(__name__)
            logger.info(
                "sentry_configured",
                environment=sentry_config["environment"],
                release=sentry_config["release"],
            )
        except ImportError:
            pass


# ============================================================================
# APM UTILITIES
# ============================================================================


def capture_exception(exception: Exception, **context: Any) -> None:
    """
    Capture exception in both Elastic APM and Sentry.

    Args:
        exception: Exception to capture
        **context: Additional context
    """
    # Elastic APM
    try:
        import elasticapm

        client = elasticapm.get_client()
        if client:
            client.capture_exception(exc_info=True, context=context)
    except (ImportError, Exception):
        pass

    # Sentry
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_exception(exception)
    except (ImportError, Exception):
        pass


def capture_message(message: str, level: str = "info", **context: Any) -> None:
    """
    Capture message in both Elastic APM and Sentry.

    Args:
        message: Message to capture
        level: Message level (debug, info, warning, error, critical)
        **context: Additional context
    """
    # Elastic APM
    try:
        import elasticapm

        client = elasticapm.get_client()
        if client:
            client.capture_message(message, level=level, custom=context)
    except (ImportError, Exception):
        pass

    # Sentry
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_message(message, level=level)
    except (ImportError, Exception):
        pass


def set_user_context(
    user_id: Any, username: str = None, email: str = None, **extra: Any
) -> None:
    """
    Set user context for APM.

    Args:
        user_id: User ID
        username: Username
        email: User email
        **extra: Additional user context
    """
    user_data = {
        "id": user_id,
        "username": username,
        "email": email,
        **extra,
    }

    # Elastic APM
    try:
        import elasticapm

        client = elasticapm.get_client()
        if client:
            client.set_user_context(user_data)
    except (ImportError, Exception):
        pass

    # Sentry
    try:
        import sentry_sdk

        sentry_sdk.set_user(user_data)
    except (ImportError, Exception):
        pass


def set_custom_context(key: str, value: Any) -> None:
    """
    Set custom context for APM.

    Args:
        key: Context key
        value: Context value
    """
    # Elastic APM
    try:
        import elasticapm

        client = elasticapm.get_client()
        if client:
            client.set_custom_context({key: value})
    except (ImportError, Exception):
        pass

    # Sentry
    try:
        import sentry_sdk

        sentry_sdk.set_context(key, value)
    except (ImportError, Exception):
        pass
