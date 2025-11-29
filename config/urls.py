"""
URL configuration for config project.

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

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from future_skills.api.monitoring import (
    HealthCheckView,
    ReadyCheckView,
    LivenessCheckView,
    VersionInfoView,
    MetricsView,
)
from config.jwt_auth import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    logout_view,
    verify_token_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # JWT Authentication
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
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

    # Backward compatibility - redirect to v2
    path("api/", include("future_skills.api.v2_urls")),

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Monitoring & Observability
    path('', include('django_prometheus.urls')),  # Prometheus metrics at /metrics
    path('health/', include('health_check.urls')),  # Django health checks at /health/
]
