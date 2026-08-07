"""DRF-level tenant resolution.

``OrganizationMiddleware`` runs before DRF authenticates the request, so for
token-authenticated API calls the tenant must be resolved again once
``request.user`` is populated. ``TenantResolutionMixin`` is applied by
``apps.common.viewsets.BaseViewSet`` through its ``initial()`` hook.
"""
from __future__ import annotations

from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from .constants import ORGANIZATION_HEADER
from .context import set_current_organization, set_current_user


def resolve_organization(request):
    """Attach ``organization``/``membership`` to an authenticated DRF request."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None

    from apps.organizations.models import Organization, OrganizationMembership

    requested_id = request.META.get(ORGANIZATION_HEADER)
    membership_qs = (
        OrganizationMembership.objects.filter(user=user, is_active=True)
        .select_related("organization")
        .order_by("created_at")
    )

    membership = None
    if requested_id:
        membership = membership_qs.filter(organization_id=requested_id).first()
    if membership is None and getattr(user, "active_organization_id", None):
        membership = membership_qs.filter(organization_id=user.active_organization_id).first()
    if membership is None:
        membership = membership_qs.first()

    if membership is not None:
        request.organization = membership.organization
        request.membership = membership
    elif user.is_superuser and requested_id:
        request.organization = Organization.objects.filter(id=requested_id).first()
        request.membership = None
    else:
        request.organization = None
        request.membership = None

    set_current_user(user)
    set_current_organization(getattr(request, "organization", None))
    return getattr(request, "organization", None)


class TenantJWTAuthentication(JWTAuthentication):
    """JWT authentication that resolves the tenant as soon as the user is known."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _token = result
            request.user = user
            resolve_organization(request)
        return result


class OrganizationHeaderAuthentication(BaseAuthentication):
    """No-op authenticator whose only job is to run tenant resolution.

    Added last in ``DEFAULT_AUTHENTICATION_CLASSES`` chains where session
    authentication is used (the browsable API, Django admin previews).
    """

    def authenticate(self, request):
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            resolve_organization(request)
        return None
