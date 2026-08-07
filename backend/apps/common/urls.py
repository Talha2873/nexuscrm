"""Shared routes mounted at the root of /api/v1/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityViewSet,
    AuditLogViewSet,
    DocumentViewSet,
    GlobalSearchView,
    NoteViewSet,
    SearchTargetsView,
    TagViewSet,
)

router = DefaultRouter()
router.register("tags", TagViewSet, basename="tag")
router.register("documents", DocumentViewSet, basename="document")
router.register("notes", NoteViewSet, basename="note")
router.register("activities", ActivityViewSet, basename="activity")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("search/", GlobalSearchView.as_view(), name="global-search"),
    path("search/targets/", SearchTargetsView.as_view(), name="search-targets"),
    path("", include(router.urls)),
]
