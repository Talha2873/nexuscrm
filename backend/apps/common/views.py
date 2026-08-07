"""Shared endpoints: health probes, tags, documents, notes, timeline, audit, search."""
from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ActivityFilter, AuditLogFilter, DocumentFilter, NoteFilter, TagFilter
from .models import Activity, AuditLog, Document, Note, Tag
from .pagination import TimelineCursorPagination
from .permissions import IsOrganizationAdmin, IsOrganizationMember
from .search import SEARCH_TARGETS, GlobalSearchService
from .serializers import (
    ActivitySerializer,
    AuditLogSerializer,
    DocumentSerializer,
    GlobalSearchResponseSerializer,
    NoteSerializer,
    TagSerializer,
)
from .viewsets import BaseReadOnlyViewSet, BaseViewSet

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------
class HealthCheckView(APIView):
    """Liveness probe: the process is up and serving."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(summary="Liveness probe", tags=["Common"], responses={200: dict})
    def get(self, request):
        return Response({"status": "ok", "service": "nexuscrm-api", "version": "1.0.0"})


class ReadinessCheckView(APIView):
    """Readiness probe: database and cache are both reachable."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(summary="Readiness probe", tags=["Common"], responses={200: dict, 503: dict})
    def get(self, request):
        checks = {"database": False, "cache": False}

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = True
        except Exception as exc:  # pragma: no cover - infrastructure failure
            logger.error("Readiness: database unavailable: %s", exc)

        try:
            cache.set("healthcheck", "ok", 10)
            checks["cache"] = cache.get("healthcheck") == "ok"
        except Exception as exc:  # pragma: no cover - infrastructure failure
            logger.error("Readiness: cache unavailable: %s", exc)

        healthy = all(checks.values())
        return Response(
            {"status": "ready" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
@extend_schema(tags=["Common"])
class TagViewSet(BaseViewSet):
    """CRUD for the tenant's tag vocabulary."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filterset_class = TagFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    audit_resource_type = "common.Tag"

    def get_queryset(self):
        return super().get_queryset().annotate(usage_count=Count("tagged_items"))


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@extend_schema(tags=["Common"])
class DocumentViewSet(BaseViewSet):
    """Upload, list, download and delete documents."""

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    filterset_class = DocumentFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "file_size", "created_at"]
    ordering = ["-created_at"]
    select_related_fields = ("uploaded_by", "content_type")
    audit_resource_type = "common.Document"

    def get_save_kwargs(self) -> dict:
        return {
            "organization": self.request.organization,
            "uploaded_by": self.request.user,
        }


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
@extend_schema(tags=["Common"])
class NoteViewSet(BaseViewSet):
    """Notes attached to any CRM record."""

    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    filterset_class = NoteFilter
    search_fields = ["body"]
    ordering_fields = ["created_at", "is_pinned"]
    ordering = ["-is_pinned", "-created_at"]
    select_related_fields = ("author", "content_type")
    audit_resource_type = "common.Note"

    def get_save_kwargs(self) -> dict:
        return {
            "organization": self.request.organization,
            "author": self.request.user,
        }


# ---------------------------------------------------------------------------
# Activity timeline
# ---------------------------------------------------------------------------
@extend_schema(tags=["Common"])
class ActivityViewSet(BaseReadOnlyViewSet):
    """Read-only organization-wide activity feed."""

    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter
    pagination_class = TimelineCursorPagination
    search_fields = ["description", "target_repr"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    select_related_fields = ("actor", "content_type")


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------
@extend_schema(tags=["Common"])
class AuditLogViewSet(BaseReadOnlyViewSet):
    """Immutable audit trail. Administrators only."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogFilter
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsOrganizationAdmin]
    search_fields = ["actor_email", "resource_type", "resource_repr", "request_path"]
    ordering_fields = ["created_at", "action"]
    ordering = ["-created_at"]
    select_related_fields = ("actor",)


# ---------------------------------------------------------------------------
# Global search
# ---------------------------------------------------------------------------
class GlobalSearchView(APIView):
    """Search every entity in the active organization with a single query."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    @extend_schema(
        summary="Global search across the CRM",
        tags=["Common"],
        parameters=[
            OpenApiParameter("q", str, description="Search term (minimum 2 characters)", required=True),
            OpenApiParameter(
                "types",
                str,
                description="Comma-separated entity keys to restrict the search, "
                "e.g. `customers,deals`.",
            ),
            OpenApiParameter("limit", int, description="Maximum results per entity type (default 5)"),
        ],
        responses={200: GlobalSearchResponseSerializer},
    )
    def get(self, request):
        term = request.query_params.get("q", "")
        raw_types = request.query_params.get("types", "")
        types = [t.strip() for t in raw_types.split(",") if t.strip()] or None
        try:
            limit = min(int(request.query_params.get("limit", 5)), 25)
        except (TypeError, ValueError):
            limit = 5

        service = GlobalSearchService(
            organization=getattr(request, "organization", None), limit_per_type=limit
        )
        results = service.search(term, types=types)

        return Response(
            {"success": True, "query": term, "total": len(results), "results": results}
        )


class SearchTargetsView(APIView):
    """List the entity types the global search supports."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Searchable entity types", tags=["Common"], responses={200: dict})
    def get(self, request):
        return Response(
            {
                "success": True,
                "results": [
                    {"key": target.key, "model": target.model_path}
                    for target in SEARCH_TARGETS
                ],
            }
        )
