"""
Centralized Logging Configuration
SmartHR360 Future Skills Platform

This module provides structured logging configuration with multiple handlers,
formatters, and processors for comprehensive application logging.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import structlog


# ============================================================================
# LOG LEVELS
# ============================================================================

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# ============================================================================
# STRUCTLOG PROCESSORS
# ============================================================================


def add_app_context(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add application context to log events."""
    event_dict["app"] = "smarthr360"
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    return event_dict


def add_log_level(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add log level to event dict."""
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def censor_sensitive_data(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Remove sensitive data from logs."""
    sensitive_keys = [
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "credit_card",
        "ssn",
        "cvv",
        "pin",
    ]

    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"

    return event_dict


# ============================================================================
# STRUCTLOG CONFIGURATION
# ============================================================================


def get_structlog_config(
    use_json: bool = True, base_dir: Path = None
) -> Dict[str, Any]:
    """
    Get structlog configuration.

    Args:
        use_json: If True, use JSON formatter. If False, use colored console.
        base_dir: Base directory for log files. If None, uses /tmp for container environments.

    Returns:
        Dict containing structlog configuration
    """
    # Use /tmp for logs in container environments if base_dir not provided
    if base_dir is None:
        log_dir = Path("/tmp/logs")
    else:
        log_dir = base_dir / "logs"

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_app_context,
        add_log_level,
        censor_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        timestamper,
    ]

    if use_json:
        # Production: JSON formatter
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        # Development: Colored console
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
                "foreign_pre_chain": shared_processors,
            },
            "plain": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "colored" if not use_json else "json",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_dir / "application.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_dir / "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "level": "ERROR",
            },
            "security_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_dir / "security.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
            },
            "performance_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_dir / "performance.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "propagate": False,
            },
            "django": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console", "file", "error_file"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.server": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False,
            },
            "future_skills": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "security": {
                "handlers": ["console", "security_file"],
                "level": "INFO",
                "propagate": False,
            },
            "performance": {
                "handlers": ["console", "performance_file"],
                "level": "INFO",
                "propagate": False,
            },
            "celery": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "apm": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }


def configure_structlog(use_json: bool = True) -> None:
    """
    Configure structlog for the application.

    Args:
        use_json: If True, use JSON formatter. If False, use colored console.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    if use_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_app_context,
            censor_sensitive_data,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# ============================================================================
# LOGSTASH CONFIGURATION
# ============================================================================


def get_logstash_handler_config(base_dir: Path = None) -> Dict[str, Any]:
    """Get Logstash handler configuration."""
    logstash_host = os.getenv("LOGSTASH_HOST", "localhost")
    logstash_port = int(os.getenv("LOGSTASH_PORT", "5000"))

    # Use /tmp for logs in container environments if base_dir not provided
    if base_dir is None:
        log_dir = Path("/tmp/logs")
    else:
        log_dir = base_dir / "logs"

    return {
        "logstash": {
            "class": "logstash_async.handler.AsynchronousLogstashHandler",
            "transport": "logstash_async.transport.TcpTransport",
            "host": logstash_host,
            "port": logstash_port,
            "database_path": str(log_dir / "logstash.db"),
            "formatter": "json",
            "level": "INFO",
        },
    }


# ============================================================================
# LOGGING UTILITIES
# ============================================================================


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def setup_logging(base_dir: Path = None) -> None:
    """
    Setup logging configuration for the application.
    Should be called during application startup.

    Args:
        base_dir: Base directory for log files. If None, uses /tmp for container environments.
    """
    # Create logs directory if it doesn't exist
    if base_dir is None:
        logs_dir = Path("/tmp/logs")
    else:
        logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Determine if we're in production
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    # Configure structlog
    configure_structlog(use_json=is_production)

    # Get logging config
    config = get_structlog_config(use_json=is_production)

    # Add Logstash handler if configured
    if os.getenv("LOGSTASH_HOST"):
        logstash_config = get_logstash_handler_config()
        config["handlers"].update(logstash_config)

        # Add logstash handler to root logger
        config["loggers"][""]["handlers"].append("logstash")

    # Apply configuration
    logging.config.dictConfig(config)

    # Log startup message
    logger = get_logger(__name__)
    logger.info(
        "logging_configured",
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        json_format=is_production,
    )


# ============================================================================
# LOG CONTEXT MANAGERS
# ============================================================================


class LogContext:
    """Context manager for adding context to logs."""

    def __init__(self, **context: Any):
        """
        Initialize log context.

        Args:
            **context: Key-value pairs to add to log context
        """
        self.context = context
        self.token = None

    def __enter__(self):
        """Enter context."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        structlog.contextvars.clear_contextvars()
        return False


# ============================================================================
# PERFORMANCE LOGGING
# ============================================================================

import time
from functools import wraps


def log_performance(logger_name: str = "performance"):
    """
    Decorator to log function performance.

    Args:
        logger_name: Name of logger to use
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    "function_completed",
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    status="success",
                )

                return result
            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    "function_failed",
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    status="error",
                    error=str(e),
                    exc_info=True,
                )

                raise

        return wrapper

    return decorator
