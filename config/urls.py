"""URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import importlib
import pkgutil

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.jwt_auth import CustomTokenObtainPairView, CustomTokenRefreshView, logout_view, verify_token_view
from future_skills.api.monitoring import (
    HealthCheckView,
    LivenessCheckView,
    MetricsView,
    ReadyCheckView,
    VersionInfoView,
)


def discover_future_skills_urls():
    future_skills_pkg = importlib.import_module("future_skills")
    discovered = []

    for module_info in pkgutil.walk_packages(future_skills_pkg.__path__, prefix="future_skills."):
        module_name = module_info.name
        if not (module_name.endswith(".urls") or "_urls" in module_name):
            continue

        module = importlib.import_module(module_name)
        suffix = module_name.removeprefix("future_skills.")

        if suffix.endswith(".urls"):
            suffix = suffix[: -len(".urls")]
        elif suffix.endswith("_urls"):
            suffix = suffix[: -len("_urls")]

        subpath = suffix.replace(".", "/")

        if subpath == "api":
            subpath = ""
        elif subpath.startswith("api/"):
            subpath = subpath[len("api/") :]

        subpath = subpath.strip("/")

        prefix = f"api/future-skills/{subpath}" if subpath else "api/future-skills/"
        if not prefix.endswith("/"):
            prefix = f"{prefix}/"

        discovered.append((prefix, module))

    discovered.sort(key=lambda item: item[0])
    return [path(prefix, include(module.__name__)) for prefix, module in discovered]


discovered_future_skills_urls = discover_future_skills_urls()

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT Authentication
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "api/auth/token/refresh/",
        CustomTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("api/auth/logout/", logout_view, name="logout"),
    path("api/auth/verify/", verify_token_view, name="token_verify"),
    # API Monitoring & Health Checks
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/ready/", ReadyCheckView.as_view(), name="ready-check"),
    path("api/alive/", LivenessCheckView.as_view(), name="liveness-check"),
    path("api/version/", VersionInfoView.as_view(), name="version-info"),
    path("api/metrics/", MetricsView.as_view(), name="api-metrics"),
    # API Versioning
    path("api/v1/", include("future_skills.api.v1_urls", namespace="v1")),
    path("api/v2/", include("future_skills.api.v2_urls", namespace="v2")),
    # Base API URLs (includes all non-versioned endpoints)
    path("api/", include("future_skills.api.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Monitoring & Observability
    path("", include("django_prometheus.urls")),  # Prometheus metrics at /metrics
    path("health/", include("health_check.urls")),  # Django health checks at /health/
    *discovered_future_skills_urls,
]
