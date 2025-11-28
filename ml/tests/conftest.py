# ml/tests/conftest.py

"""
Pytest configuration and fixtures for ML tests.

Imports fixtures from the main tests/conftest.py to make them available
for ML-specific tests.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path to import from tests.conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import fixtures from main conftest
from tests.conftest import (
    sample_skill,
    sample_job_role,
    sample_future_skill_prediction,
    regular_user,
    admin_user,
)

# Re-export fixtures so they're available in ml/tests
__all__ = [
    'sample_skill',
    'sample_job_role',
    'sample_future_skill_prediction',
    'regular_user',
    'admin_user',
]
