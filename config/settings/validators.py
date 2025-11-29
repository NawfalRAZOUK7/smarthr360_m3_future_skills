"""
Environment variable validation and configuration management.

This module provides comprehensive validation for environment variables,
ensuring all required configuration is present and correctly formatted.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from decouple import config


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class EnvironmentValidator:
    """Validates environment variables and configuration settings."""

    def __init__(self, environment: str = 'development'):
        """
        Initialize the environment validator.

        Args:
            environment: The environment name (development, production, test)
        """
        self.environment = environment
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_required(self, var_name: str, var_value: Any, var_type: type = str) -> bool:
        """
        Validate that a required variable exists and has the correct type.

        Args:
            var_name: Name of the environment variable
            var_value: Current value of the variable
            var_type: Expected type of the variable

        Returns:
            True if valid, False otherwise
        """
        if var_value is None or (isinstance(var_value, str) and not var_value.strip()):
            self.errors.append(f"❌ {var_name} is required but not set")
            return False

        if not isinstance(var_value, var_type):
            self.errors.append(
                f"❌ {var_name} has incorrect type. Expected {var_type.__name__}, got {type(var_value).__name__}"
            )
            return False

        return True

    def validate_optional(self, var_name: str, var_value: Any, var_type: type = str) -> bool:
        """
        Validate an optional variable if it exists.

        Args:
            var_name: Name of the environment variable
            var_value: Current value of the variable
            var_type: Expected type of the variable

        Returns:
            True if valid or not set, False if set incorrectly
        """
        if var_value is None or (isinstance(var_value, str) and not var_value.strip()):
            return True

        if not isinstance(var_value, var_type):
            self.warnings.append(
                f"⚠️  {var_name} has incorrect type. Expected {var_type.__name__}, got {type(var_value).__name__}"
            )
            return False

        return True

    def validate_path(self, var_name: str, path: Path, must_exist: bool = False) -> bool:
        """
        Validate that a path is valid and optionally exists.

        Args:
            var_name: Name of the environment variable
            path: Path to validate
            must_exist: Whether the path must already exist

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(path, (str, Path)):
            self.errors.append(f"❌ {var_name} must be a valid path")
            return False

        path = Path(path)

        if must_exist and not path.exists():
            self.errors.append(f"❌ {var_name} path does not exist: {path}")
            return False

        if must_exist and path.is_file():
            # Check if file is readable
            try:
                with open(path, 'r') as f:
                    pass
            except Exception as e:
                self.errors.append(f"❌ {var_name} file is not readable: {e}")
                return False

        return True

    def validate_url(self, var_name: str, url: str, schemes: Optional[List[str]] = None) -> bool:
        """
        Validate that a URL is properly formatted.

        Args:
            var_name: Name of the environment variable
            url: URL to validate
            schemes: List of allowed schemes (e.g., ['http', 'https'])

        Returns:
            True if valid, False otherwise
        """
        if not url:
            return True

        if schemes:
            if not any(url.startswith(f"{scheme}://") for scheme in schemes):
                self.errors.append(
                    f"❌ {var_name} must use one of these schemes: {', '.join(schemes)}"
                )
                return False

        return True

    def validate_choice(self, var_name: str, value: str, choices: List[str]) -> bool:
        """
        Validate that a value is one of the allowed choices.

        Args:
            var_name: Name of the environment variable
            value: Value to validate
            choices: List of allowed values

        Returns:
            True if valid, False otherwise
        """
        if value not in choices:
            self.errors.append(
                f"❌ {var_name} must be one of: {', '.join(choices)}. Got: {value}"
            )
            return False

        return True

    def validate_all(self) -> Dict[str, Any]:
        """
        Run all validation checks for the current environment.

        Returns:
            Dictionary with validation results
        """
        from decouple import config, Csv
        from pathlib import Path

        # Base directory
        BASE_DIR = Path(__file__).resolve().parent.parent.parent

        # Common validations (all environments)
        self._validate_common(config, Csv, BASE_DIR)

        # Environment-specific validations
        if self.environment == 'production':
            self._validate_production(config, Csv, BASE_DIR)
        elif self.environment == 'development':
            self._validate_development(config, Csv, BASE_DIR)
        elif self.environment == 'test':
            self._validate_test(config, Csv, BASE_DIR)

        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'environment': self.environment,
        }

    def _validate_common(self, config, Csv, BASE_DIR):
        """Validate common settings for all environments."""
        # SECRET_KEY is always required
        secret_key = config('SECRET_KEY', default='')
        self.validate_required('SECRET_KEY', secret_key, str)

        if len(secret_key) < 50:
            self.warnings.append('⚠️  SECRET_KEY should be at least 50 characters long')

        # DEBUG
        debug = config('DEBUG', default=False, cast=bool)
        self.validate_optional('DEBUG', debug, bool)

        # ALLOWED_HOSTS
        allowed_hosts = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
        if not allowed_hosts:
            self.warnings.append('⚠️  ALLOWED_HOSTS is empty')

        # Database
        database_url = config('DATABASE_URL', default=None)
        if database_url:
            self.validate_url('DATABASE_URL', database_url, ['postgresql', 'sqlite', 'mysql'])

        # Celery
        celery_broker = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
        self.validate_url('CELERY_BROKER_URL', celery_broker, ['redis', 'amqp'])

        celery_backend = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
        self.validate_url('CELERY_RESULT_BACKEND', celery_backend, ['redis', 'amqp'])

        # ML Settings
        ml_model_path = BASE_DIR / "ml" / "models" / "future_skills_model.pkl"
        use_ml = config('FUTURE_SKILLS_USE_ML', default=True, cast=bool)

        if use_ml and not ml_model_path.exists():
            self.warnings.append(
                f'⚠️  FUTURE_SKILLS_USE_ML is True but model file does not exist: {ml_model_path}'
            )

    def _validate_production(self, config, Csv, BASE_DIR):
        """Validate production-specific settings."""
        # DEBUG must be False
        debug = config('DEBUG', default=False, cast=bool)
        if debug:
            self.errors.append('❌ DEBUG must be False in production')

        # ALLOWED_HOSTS must be set
        allowed_hosts = config('ALLOWED_HOSTS', default='', cast=Csv())
        if not allowed_hosts:
            self.errors.append('❌ ALLOWED_HOSTS must be explicitly set in production')

        # DATABASE_URL is required
        database_url = config('DATABASE_URL', default=None)
        if not database_url:
            self.errors.append('❌ DATABASE_URL is required in production')
        elif not database_url.startswith('postgresql://'):
            self.warnings.append('⚠️  PostgreSQL is recommended for production')

        # Security settings
        ssl_redirect = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
        if not ssl_redirect:
            self.warnings.append('⚠️  SECURE_SSL_REDIRECT should be True in production')

        session_cookie_secure = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
        if not session_cookie_secure:
            self.warnings.append('⚠️  SESSION_COOKIE_SECURE should be True in production')

        csrf_cookie_secure = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
        if not csrf_cookie_secure:
            self.warnings.append('⚠️  CSRF_COOKIE_SECURE should be True in production')

        # Email settings
        email_backend = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
        if email_backend == 'django.core.mail.backends.console.EmailBackend':
            self.warnings.append('⚠️  Console email backend is not suitable for production')

        # CORS settings
        cors_origins = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())
        if not cors_origins:
            self.warnings.append('⚠️  CORS_ALLOWED_ORIGINS should be explicitly set in production')

    def _validate_development(self, config, Csv, BASE_DIR):
        """Validate development-specific settings."""
        # No strict requirements for development
        pass

    def _validate_test(self, config, Csv, BASE_DIR):
        """Validate test-specific settings."""
        # Test environment should use simpler backends
        pass

    def print_results(self):
        """Print validation results to console."""
        print("\n" + "=" * 70)
        print(f"🔍 Environment Configuration Validation: {self.environment.upper()}")
        print("=" * 70)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All configuration checks passed!")

        print("\n" + "=" * 70 + "\n")

        return len(self.errors) == 0


def validate_environment(environment: str = 'development', exit_on_error: bool = False) -> bool:
    """
    Validate environment configuration and optionally exit on errors.

    Args:
        environment: Environment name (development, production, test)
        exit_on_error: Whether to exit the process if validation fails

    Returns:
        True if validation passed, False otherwise
    """
    validator = EnvironmentValidator(environment)
    results = validator.validate_all()
    validator.print_results()

    if not results['valid'] and exit_on_error:
        print("❌ Configuration validation failed. Please fix the errors above.")
        sys.exit(1)

    return results['valid']


def get_env_info() -> Dict[str, Any]:
    """
    Get current environment configuration information.

    Returns:
        Dictionary with current configuration
    """
    from decouple import config, Csv
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    return {
        'environment': os.getenv('DJANGO_SETTINGS_MODULE', 'unknown'),
        'debug': config('DEBUG', default=False, cast=bool),
        'secret_key_set': bool(config('SECRET_KEY', default='')),
        'secret_key_length': len(config('SECRET_KEY', default='')),
        'allowed_hosts': config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv()),
        'database_url_set': bool(config('DATABASE_URL', default=None)),
        'celery_broker': config('CELERY_BROKER_URL', default='redis://localhost:6379/0'),
        'use_ml': config('FUTURE_SKILLS_USE_ML', default=True, cast=bool),
        'ml_model_exists': (BASE_DIR / "ml" / "models" / "future_skills_model.pkl").exists(),
    }


def print_env_info():
    """Print current environment configuration."""
    info = get_env_info()

    print("\n" + "=" * 70)
    print("📋 Current Environment Configuration")
    print("=" * 70)
    print(f"Environment: {info['environment']}")
    print(f"Debug Mode: {info['debug']}")
    print(f"Secret Key: {'✅ Set' if info['secret_key_set'] else '❌ Not Set'} ({info['secret_key_length']} chars)")
    print(f"Allowed Hosts: {', '.join(info['allowed_hosts'])}")
    print(f"Database URL: {'✅ Set' if info['database_url_set'] else '❌ Not Set (using default)'}")
    print(f"Celery Broker: {info['celery_broker']}")
    print(f"Use ML: {info['use_ml']}")
    print(f"ML Model: {'✅ Exists' if info['ml_model_exists'] else '❌ Not Found'}")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    """Run validation from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Validate environment configuration')
    parser.add_argument(
        '--env',
        choices=['development', 'production', 'test'],
        default='development',
        help='Environment to validate (default: development)'
    )
    parser.add_argument(
        '--exit-on-error',
        action='store_true',
        help='Exit with error code if validation fails'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Print current environment information'
    )

    args = parser.parse_args()

    if args.info:
        print_env_info()
    else:
        validate_environment(args.env, args.exit_on_error)
