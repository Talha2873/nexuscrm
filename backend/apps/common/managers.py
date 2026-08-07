"""Querysets and managers implementing soft deletion and tenant scoping."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from .context import get_current_organization_id


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet whose ``delete()`` marks rows deleted instead of removing them."""

    def delete(self):  # type: ignore[override]
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently remove the rows (used by retention/GDPR jobs)."""
        return super().delete()

    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(is_deleted=False)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(is_deleted=True)

    def restore(self):
        return self.update(is_deleted=False, deleted_at=None)


class TenantQuerySet(SoftDeleteQuerySet):
    """Adds explicit organization scoping helpers."""

    def for_organization(self, organization) -> "TenantQuerySet":
        """Restrict to a single tenant. Accepts an instance, an id, or ``None``."""
        if organization is None:
            return self.none()
        organization_id = getattr(organization, "id", organization)
        return self.filter(organization_id=organization_id)

    def for_current_organization(self) -> "TenantQuerySet":
        """Restrict to the organization held in the thread-local context."""
        return self.for_organization(get_current_organization_id())


class SoftDeleteManager(models.Manager):
    """Default manager: hides soft-deleted rows unless ``with_deleted=True``."""

    queryset_class = SoftDeleteQuerySet

    def __init__(self, *args, with_deleted: bool = False, **kwargs):
        self.with_deleted = with_deleted
        super().__init__(*args, **kwargs)

    def get_queryset(self) -> SoftDeleteQuerySet:
        queryset = self.queryset_class(self.model, using=self._db)
        if self.with_deleted:
            return queryset
        return queryset.filter(is_deleted=False)

    def alive(self):
        return self.get_queryset().alive()

    def dead(self):
        return self.queryset_class(self.model, using=self._db).dead()

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class TenantManager(SoftDeleteManager):
    """Manager for organization-scoped models."""

    queryset_class = TenantQuerySet

    def for_organization(self, organization) -> TenantQuerySet:
        return self.get_queryset().for_organization(organization)

    def for_current_organization(self) -> TenantQuerySet:
        return self.get_queryset().for_current_organization()
