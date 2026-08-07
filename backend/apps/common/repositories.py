"""Repository layer.

Repositories are the *only* place that talks to the ORM. Services depend on
repositories, never on querysets directly, which keeps the domain logic testable
and makes tenant scoping impossible to forget: every read goes through
``get_queryset()``, which is already organization-filtered.
"""
from __future__ import annotations

from typing import Any, Generic, Iterable, Sequence, TypeVar

from django.db import transaction
from django.db.models import Model, Q, QuerySet
from django.shortcuts import get_object_or_404

from .context import get_current_organization

ModelType = TypeVar("ModelType", bound=Model)


class BaseRepository(Generic[ModelType]):
    """Generic persistence gateway for a single model."""

    model: type[ModelType]
    #: Relations eagerly joined on every read (avoids N+1).
    select_related: Sequence[str] = ()
    prefetch_related: Sequence[str] = ()
    default_ordering: Sequence[str] = ("-created_at",)

    def __init__(self, model: type[ModelType] | None = None) -> None:
        if model is not None:
            self.model = model
        if not getattr(self, "model", None):
            raise ValueError(f"{self.__class__.__name__} requires a `model` attribute.")

    # ------------------------------------------------------------------
    # Queryset construction
    # ------------------------------------------------------------------
    def get_base_queryset(self, include_deleted: bool = False) -> QuerySet[ModelType]:
        manager = self.model.all_objects if include_deleted else self.model.objects
        queryset = manager.all()
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        if self.default_ordering:
            queryset = queryset.order_by(*self.default_ordering)
        return queryset

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[ModelType]:
        """Tenant-scoped queryset. Override for non-tenant models."""
        queryset = self.get_base_queryset(include_deleted=include_deleted)
        if self._is_tenant_model():
            organization = get_current_organization()
            if organization is None:
                return queryset.none()
            queryset = queryset.filter(organization_id=organization.id)
        return queryset

    def for_organization(self, organization, include_deleted: bool = False) -> QuerySet[ModelType]:
        """Explicit tenant scoping, for Celery tasks and management commands."""
        queryset = self.get_base_queryset(include_deleted=include_deleted)
        if not self._is_tenant_model():
            return queryset
        if organization is None:
            return queryset.none()
        organization_id = getattr(organization, "id", organization)
        return queryset.filter(organization_id=organization_id)

    def _is_tenant_model(self) -> bool:
        return any(field.name == "organization" for field in self.model._meta.fields)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def all(self) -> QuerySet[ModelType]:
        return self.get_queryset()

    def filter(self, **filters: Any) -> QuerySet[ModelType]:
        return self.get_queryset().filter(**filters)

    def exclude(self, **filters: Any) -> QuerySet[ModelType]:
        return self.get_queryset().exclude(**filters)

    def search(self, term: str, fields: Iterable[str]) -> QuerySet[ModelType]:
        if not term:
            return self.get_queryset()
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": term})
        return self.get_queryset().filter(query)

    def get_by_id(self, pk: Any, include_deleted: bool = False) -> ModelType | None:
        return self.get_queryset(include_deleted=include_deleted).filter(pk=pk).first()

    def get_or_404(self, pk: Any) -> ModelType:
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_by(self, **filters: Any) -> ModelType | None:
        return self.get_queryset().filter(**filters).first()

    def exists(self, **filters: Any) -> bool:
        return self.get_queryset().filter(**filters).exists()

    def count(self, **filters: Any) -> int:
        queryset = self.get_queryset()
        return queryset.filter(**filters).count() if filters else queryset.count()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    @transaction.atomic
    def create(self, **payload: Any) -> ModelType:
        if self._is_tenant_model() and "organization" not in payload and "organization_id" not in payload:
            organization = get_current_organization()
            if organization is not None:
                payload["organization"] = organization
        instance = self.model(**payload)
        instance.full_clean(exclude=self._clean_exclusions())
        instance.save()
        return instance

    @transaction.atomic
    def bulk_create(self, payloads: Sequence[dict[str, Any]]) -> list[ModelType]:
        organization = get_current_organization() if self._is_tenant_model() else None
        instances = []
        for payload in payloads:
            data = dict(payload)
            if organization is not None and "organization" not in data and "organization_id" not in data:
                data["organization"] = organization
            instances.append(self.model(**data))
        return self.model.objects.bulk_create(instances)

    @transaction.atomic
    def update(self, instance: ModelType, **payload: Any) -> ModelType:
        changed: list[str] = []
        for field, value in payload.items():
            if getattr(instance, field, None) != value:
                setattr(instance, field, value)
                changed.append(field)
        if changed:
            instance.full_clean(exclude=self._clean_exclusions())
            instance.save()
        return instance

    @transaction.atomic
    def update_or_create(self, defaults: dict[str, Any] | None = None, **lookup: Any):
        defaults = defaults or {}
        if self._is_tenant_model() and "organization" not in lookup:
            organization = get_current_organization()
            if organization is not None:
                lookup["organization"] = organization
        return self.model.objects.update_or_create(defaults=defaults, **lookup)

    @transaction.atomic
    def delete(self, instance: ModelType, hard: bool = False) -> None:
        if hard:
            instance.delete(hard=True)
        else:
            instance.delete()

    @transaction.atomic
    def restore(self, instance: ModelType) -> ModelType:
        instance.restore()
        return instance

    def _clean_exclusions(self) -> list[str]:
        """Skip validation of auto-populated / relational bookkeeping fields."""
        return [
            field.name
            for field in self.model._meta.fields
            if field.name in {"created_by", "updated_by", "deleted_by", "organization"}
        ]
