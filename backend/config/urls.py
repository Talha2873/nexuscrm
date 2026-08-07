"""Root URL configuration for NexusCRM."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common.views import HealthCheckView, ReadinessCheckView

admin.site.site_header = "NexusCRM Administration"
admin.site.site_title = "NexusCRM Admin"
admin.site.index_title = "Platform administration"

urlpatterns = [
    # ---------- Django admin ----------
    path("admin/", admin.site.urls),
    # ---------- Health probes ----------
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("ready/", ReadinessCheckView.as_view(), name="readiness-check"),
    # ---------- API v1 ----------
    path("api/v1/", include(("config.api_urls", "v1"), namespace="v1")),
    # ---------- OpenAPI schema & docs ----------
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
