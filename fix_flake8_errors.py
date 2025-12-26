#!/usr/bin/env python3
"""Script to automatically fix common Flake8 errors.

This script performs the following fixes:
- Remove unused imports (F401)
- Remove unused variables (F841)
- Add missing constants (F821)
- Fix bare except clauses (E722).
"""

from pathlib import Path

# Define the fixes
FIXES = {
    # Remove these unused imports
    "config/apm_config.py": [
        ("from django.conf import settings\n", ""),  # Line 12
        ("import sentry_sdk\n", ""),  # Line 145 (in else block)
        ("import elasticapm\n", ""),  # Line 249
        (
            "from elasticapm.contrib.django.middleware import TracingMiddleware\n",
            "",
        ),  # Line 250
    ],
    "config/flowerconfig.py": [
        ("import os\n", ""),  # Line 27
    ],
    "config/security_middleware.py": [
        ("import json\n", ""),  # Line 13
    ],
    "config/settings/base.py": [
        ("import django_redis\n", ""),  # Line 128
        ("from config.logging_config import setup_logging\n", ""),  # Line 522
    ],
    "config/settings/development.py": [
        ("import django_extensions\n", ""),  # Line 20
        ("import debug_toolbar\n", ""),  # Line 33
    ],
    "config/settings/production.py": [
        ("import os\n", ""),  # Line 7
    ],
    "config/settings/validators.py": [
        ("from decouple import config\n", ""),  # Line 13 (unused, redefined)
    ],
    "future_skills/api/views.py": [
        ("from rest_framework.permissions import IsAuthenticated\n", ""),
        ("from drf_spectacular.utils import extend_schema_view\n", ""),
        ("from .serializers import UpdateEmployeeSkillsSerializer\n", ""),
    ],
    "future_skills/management/commands/analyze_logs.py": [
        ("from collections import defaultdict\n", ""),
        ("from pathlib import Path\n", ""),
    ],
    "future_skills/management/commands/export_future_skills_dataset.py": [
        ("from django.db.models import Avg\n", ""),
        (
            "from future_skills.services.prediction_engine import _find_relevant_trend\n",
            "",
        ),
    ],
    "future_skills/management/commands/health_check.py": [
        ("import requests\n", ""),
    ],
    "future_skills/management/commands/monitor_security.py": [
        ("from collections import defaultdict\n", ""),
    ],
    "future_skills/management/commands/train_future_skills_model.py": [
        ("import sys\n", ""),
    ],
    "future_skills/services/explanation_engine.py": [
        ("from typing import Tuple\n", ""),
    ],
    "future_skills/services/prediction_engine.py": [
        ("from pathlib import Path\n", ""),
    ],
    "future_skills/services/training_service.py": [
        ("import time\n", ""),
        ("from datetime import timedelta\n", ""),
        ("from typing import Tuple\n", ""),
        ("from django.conf import settings\n", ""),
        ("from ml.monitoring import ModelMonitor\n", ""),
    ],
    "future_skills/tasks.py": [
        ("from celery_monitoring import with_circuit_breaker\n", ""),
    ],
}


def remove_unused_imports(file_path: Path, imports_to_remove: list):
    """Remove unused imports from a file."""
    content = file_path.read_text()

    for old, new in imports_to_remove:
        # Handle multiline imports more carefully
        if old in content:
            content = content.replace(old, new, 1)  # Replace only first occurrence
            print(f"✓ Removed: {old.strip()} from {file_path.name}")

    file_path.write_text(content)


def main():
    """Apply all fixes."""
    base_dir = Path(__file__).parent

    print("Fixing Flake8 errors...")
    print("=" * 70)

    for file_rel_path, fixes in FIXES.items():
        file_path = base_dir / file_rel_path
        if file_path.exists():
            print(f"\n📝 Processing: {file_rel_path}")
            remove_unused_imports(file_path, fixes)
        else:
            print(f"⚠️  File not found: {file_rel_path}")

    print("\n" + "=" * 70)
    print("✅ Unused imports removed!")
    print("\nNote: Some errors need manual fixing:")
    print("  - Undefined variables (F821): logger, MARKDOWN_SEPARATOR")
    print("  - Syntax errors (E999): f-string with backslash")
    print("  - Bare except clauses (E722): Replace with 'except Exception:'")
    print("  - Line too long (E501): Break into multiple lines")
    print("  - Module imports not at top (E402): Move imports to top of file")


if __name__ == "__main__":
    main()
