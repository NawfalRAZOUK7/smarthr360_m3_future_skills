"""
Management command to validate environment configuration.

Usage:
    python manage.py validate_config
    python manage.py validate_config --env production
    python manage.py validate_config --info
"""

from django.core.management.base import BaseCommand
from config.settings.validators import validate_environment, print_env_info


class Command(BaseCommand):
    help = 'Validate environment configuration and settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--env',
            type=str,
            choices=['development', 'production', 'test'],
            help='Specify environment to validate (auto-detected if not provided)',
        )
        parser.add_argument(
            '--info',
            action='store_true',
            help='Print current environment information',
        )
        parser.add_argument(
            '--exit-on-error',
            action='store_true',
            help='Exit with error code if validation fails',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        if options['info']:
            print_env_info()
            return

        # Auto-detect environment if not specified
        env = options.get('env')
        if not env:
            import os
            settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
            if 'production' in settings_module:
                env = 'production'
            elif 'test' in settings_module:
                env = 'test'
            else:
                env = 'development'

            self.stdout.write(f"Auto-detected environment: {env}")

        # Run validation
        is_valid = validate_environment(env, exit_on_error=options['exit_on_error'])

        if is_valid:
            self.stdout.write(self.style.SUCCESS('\n✅ Configuration validation passed!\n'))
        else:
            self.stdout.write(self.style.ERROR('\n❌ Configuration validation failed!\n'))
            if options['exit_on_error']:
                exit(1)
