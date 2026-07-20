"""Test profile backed by Postgres, for the platform end-to-end run.

``config.settings.test`` uses in-memory SQLite: fast, isolated, and the right
default for local runs and pytest. But the async prediction path spawns a real
worker thread (``future_skills/services/prediction_runs.py``), and SQLite
cannot serve two concurrent writers -- the run dies with "database table is
locked: future_skills_predictionrun". That surfaces as a load-sensitive flake:
it passes on an idle runner and fails when the whole compose stack is
competing for CPU.

Production runs Postgres, which handles concurrent writers, so the platform
e2e exercises the suite against the real engine rather than tuning SQLite to
approximate one. Everything else is inherited from the standard test profile.

Selected explicitly with ``manage.py test --settings=config.settings.test_postgres``;
manage.py honours a CLI --settings over its automatic test profile.
"""

import os

import dj_database_url

from .test import *  # noqa: F403,S2208 - standard Django settings pattern

DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"]),
}
