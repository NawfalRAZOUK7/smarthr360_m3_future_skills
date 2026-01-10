"""Refresh slice performance metrics via the API endpoint."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Refresh slice metrics by calling the API refresh endpoint."""

    help = "Refresh future skills slice metrics via the API (login + refresh)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default="http://localhost:8000",
            help="Base URL of the API (default: http://localhost:8000).",
        )
        parser.add_argument(
            "--email",
            default=None,
            help="Email for API login (required if --token not provided).",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="Password for API login (required if --token not provided).",
        )
        parser.add_argument(
            "--token",
            default=None,
            help="Access token to use instead of logging in.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=10,
            help="Request timeout in seconds (default: 10).",
        )

    def handle(self, *args, **options):
        base_url = (options["base_url"] or "").rstrip("/")
        if not base_url:
            raise CommandError("base-url must not be empty.")

        token = options.get("token")
        timeout = int(options["timeout"]) if options.get("timeout") else 10

        if not token:
            email = options.get("email")
            password = options.get("password")
            if not email or not password:
                raise CommandError("Provide --token or both --email and --password.")
            token = self._login(base_url, email, password, timeout)

        response = self._refresh(base_url, token, timeout)
        self.stdout.write(self.style.SUCCESS(json.dumps(response, ensure_ascii=True)))

    def _login(self, base_url: str, email: str, password: str, timeout: int) -> str:
        url = f"{base_url}/api/auth/login/"
        payload = json.dumps({"email": email, "password": password}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        data = self._post_json(url, payload, headers, timeout)
        token = data.get("access")
        if not token:
            raise CommandError("Login succeeded but access token missing in response.")
        return token

    def _refresh(self, base_url: str, token: str, timeout: int) -> dict:
        url = f"{base_url}/api/metrics/slice-performance/refresh/"
        headers = {"Authorization": f"Bearer {token}"}
        payload = json.dumps({}).encode("utf-8")
        return self._post_json(url, payload, headers, timeout)

    def _post_json(self, url: str, payload: bytes, headers: dict, timeout: int) -> dict:
        request = Request(url, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise CommandError(f"Request failed ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise CommandError(f"Request failed: {exc.reason}") from exc

        if not body:
            raise CommandError("Empty response from server.")

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON response: {body}") from exc
