"""Reusable django-filter filtersets and DRF filter backends."""
from __future__ import annotations

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from .models import Activity, AuditLog, Document, Note, Tag


class BaseFilterSet(filters.FilterSet):
    """Adds created/updated range filters to every list endpoint."""

    created_after = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    updated_after = filters.DateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = filters.DateTimeFilter(field_name="updated_at", lookup_expr="lte")
    created_by = filters.UUIDFilter(field_name="created_by_id")


class TagFilter(BaseFilterSet):
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Tag
        fields = ["name", "slug", "color"]


class DocumentFilter(BaseFilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    category = filters.CharFilter()
    uploaded_by = filters.UUIDFilter(field_name="uploaded_by_id")
    object_id = filters.UUIDFilter()
    content_type = filters.CharFilter(method="filter_content_type")
    min_size = filters.NumberFilter(field_name="file_size", lookup_expr="gte")
    max_size = filters.NumberFilter(field_name="file_size", lookup_expr="lte")

    class Meta:
        model = Document
        fields = ["name", "category", "is_public", "uploaded_by", "object_id"]

    def filter_content_type(self, queryset, name, value):
        if not value or "." not in value:
            return queryset
        app_label, model = value.lower().split(".", 1)
        return queryset.filter(
            content_type__app_label=app_label, content_type__model=model
        )


class NoteFilter(BaseFilterSet):
    object_id = filters.UUIDFilter()
    is_pinned = filters.BooleanFilter()
    author = filters.UUIDFilter(field_name="author_id")

    class Meta:
        model = Note
        fields = ["object_id", "is_pinned", "author"]


class ActivityFilter(BaseFilterSet):
    verb = filters.MultipleChoiceFilter(choices=Activity._meta.get_field("verb").choices)
    actor = filters.UUIDFilter(field_name="actor_id")
    object_id = filters.UUIDFilter()
    content_type = filters.CharFilter(method="filter_content_type")

    class Meta:
        model = Activity
        fields = ["verb", "actor", "object_id"]

    def filter_content_type(self, queryset, name, value):
        if not value or "." not in value:
            return queryset
        app_label, model = value.lower().split(".", 1)
        return queryset.filter(
            content_type__app_label=app_label, content_type__model=model
        )


class AuditLogFilter(BaseFilterSet):
    action = filters.MultipleChoiceFilter(choices=AuditLog._meta.get_field("action").choices)
    actor = filters.UUIDFilter(field_name="actor_id")
    resource_type = filters.CharFilter(lookup_expr="icontains")
    resource_id = filters.CharFilter()
    ip_address = filters.CharFilter()

    class Meta:
        model = AuditLog
        fields = ["action", "actor", "resource_type", "resource_id", "status_code"]


class OrganizationScopedBackend(BaseFilterBackend):
    """Belt-and-braces tenant filter applied after every other backend.

    Repositories already scope reads; this backend guarantees the same for any
    view that builds a queryset directly.
    """

    def filter_queryset(self, request, queryset, view):
        model = queryset.model
        if not any(field.name == "organization" for field in model._meta.fields):
            return queryset
        if request.user.is_superuser and request.query_params.get("all_organizations"):
            return queryset
        organization = getattr(request, "organization", None)
        if organization is None:
            return queryset.none()
        return queryset.filter(organization_id=organization.id)


class SoftDeleteBackend(BaseFilterBackend):
    """Optionally include soft-deleted rows with ``?include_deleted=true``."""

    def filter_queryset(self, request, queryset, view):
        include_deleted = str(
            request.query_params.get("include_deleted", "")
        ).lower() in {"1", "true", "yes"}
        if include_deleted and request.user.is_staff:
            return queryset
        return queryset.filter(is_deleted=False)
