"""Base ViewSets wiring together tenancy, permissions, mixins and services."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .authentication import resolve_organization
from .filters import OrganizationScopedBackend
from .mixins import (
    AttachmentMixin,
    AuditMixin,
    BulkActionMixin,
    MultiSerializerMixin,
    SoftDeleteMixin,
    TimelineMixin,
)
from .permissions import IsOrganizationMember, ReadOnlyForViewers


class BaseViewSet(
    MultiSerializerMixin,
    AuditMixin,
    SoftDeleteMixin,
    BulkActionMixin,
    viewsets.ModelViewSet,
):
    """Full CRUD, organization-scoped, audited and soft-deleting.

    Concrete viewsets only need to declare ``queryset``, ``serializer_class``,
    ``filterset_class``, ``search_fields`` and ``ordering_fields``.
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, ReadOnlyForViewers]
    filter_backends = list(viewsets.ModelViewSet.filter_backends) + [OrganizationScopedBackend]
    #: Relations to eagerly load on list/retrieve.
    select_related_fields: tuple[str, ...] = ()
    prefetch_related_fields: tuple[str, ...] = ()
    service_class = None

    def initial(self, request, *args, **kwargs):
        """Resolve the tenant before permission checks and queryset access."""
        super().initial(request, *args, **kwargs)
        if getattr(request, "organization", None) is None:
            resolve_organization(request)

    def get_service(self):
        if self.service_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define `service_class` to use get_service()."
            )
        return self.service_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = getattr(self.request, "organization", None)
        context["membership"] = getattr(self.request, "membership", None)
        return context


class BaseCRMViewSet(BaseViewSet, TimelineMixin, AttachmentMixin):
    """A :class:`BaseViewSet` that also exposes timeline, notes and documents.

    Used by every customer-facing entity (customers, contacts, companies,
    deals, projects, tasks, tickets).
    """


class BaseReadOnlyViewSet(
    MultiSerializerMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """List/retrieve only, still organization-scoped."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filter_backends = list(viewsets.ReadOnlyModelViewSet.filter_backends) + [
        OrganizationScopedBackend
    ]
    select_related_fields: tuple[str, ...] = ()
    prefetch_related_fields: tuple[str, ...] = ()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if getattr(request, "organization", None) is None:
            resolve_organization(request)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        return queryset
