"""
Smoke tests for API v2 routing and observability endpoints.

Ensures that the v2 paths remain reachable and basic auth/health/metrics
endpoints respond as expected.
"""

import pytest


@pytest.mark.django_db
class TestAuthAndHealth:
    def test_auth_token_obtain(self, api_client, hr_manager):
        payload = {"username": "hr_manager", "password": "hrpass123"}
        response = api_client.post("/api/auth/token/", payload, format="json")
        assert response.status_code == 200
        body = response.json()
        assert "access" in body and "refresh" in body

    def test_health_endpoints(self, api_client):
        for path in [
            "/api/health/",
            "/api/ready/",
            "/api/alive/",
            "/api/version/",
        ]:
            resp = api_client.get(path)
            assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    def test_health_metrics_staff_only(self, api_client, hr_manager):
        api_client.force_authenticate(user=hr_manager)
        resp = api_client.get("/api/metrics/")
        assert resp.status_code == 200

    def test_prometheus_metrics(self, api_client):
        resp = api_client.get("/metrics")
        assert resp.status_code == 200
        # Prometheus text format should contain a metric name such as python_info
        assert (
            b"python_info" in resp.content
            or b"process_resident_memory_bytes" in resp.content
        )


@pytest.mark.django_db
class TestApiV2Routing:
    def _auth_hr_manager(self, api_client, hr_manager):
        api_client.force_authenticate(user=hr_manager)
        return api_client

    def test_v2_predictions_list(self, api_client, hr_manager):
        client = self._auth_hr_manager(api_client, hr_manager)
        resp = client.get("/api/v2/predictions/")
        assert resp.status_code == 200

    def test_v2_recommendations_list(self, api_client, hr_manager):
        client = self._auth_hr_manager(api_client, hr_manager)
        resp = client.get("/api/v2/recommendations/")
        assert resp.status_code == 200

    def test_v2_training_runs_list(self, api_client, hr_manager):
        client = self._auth_hr_manager(api_client, hr_manager)
        resp = client.get("/api/v2/ml/training-runs/")
        assert resp.status_code == 200
