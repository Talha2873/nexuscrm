"""Request middleware: correlation IDs, tenant resolution and audit logging."""
from __future__ import annotations

import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

from .constants import ORGANIZATION_HEADER, REQUEST_ID_HEADER, AuditAction
from .context import (
    clear_current_context,
    set_current_organization,
    set_current_request,
    set_current_user,
    set_request_id,
)

logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """Attach a correlation id to every request/response and log line."""

    def process_request(self, request):
        request_id = request.META.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id
        request.started_at = time.monotonic()
        set_request_id(request_id)
        return None

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        started_at = getattr(request, "started_at", None)
        if started_at is not None:
            duration_ms = (time.monotonic() - started_at) * 1000
            response["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
            if duration_ms > 1000:
                logger.warning(
                    "Slow request %s %s took %.0fms", request.method, request.path, duration_ms
                )
        return response


class CurrentRequestMiddleware(MiddlewareMixin):
    """Publish the request/user into thread-local storage, then clear it."""

    def process_request(self, request):
        set_current_request(request)
        set_current_user(getattr(request, "user", None))
        return None

    def process_response(self, request, response):
        clear_current_context()
        return response

    def process_exception(self, request, exception):
        clear_current_context()
        return None


class OrganizationMiddleware(MiddlewareMixin):
    """Resolve the active tenant for the request.

    Resolution order:

    1. ``X-Organization-Id`` header (lets the UI switch tenants per request).
    2. The user's ``active_organization``.
    3. The user's first active membership.

    The resolved organization and membership are attached to the request and
    published to the thread-local context so repositories can scope reads.
    """

    def process_request(self, request):
        request.organization = None
        request.membership = None
        set_current_organization(None)

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        # DRF authenticates lazily inside the view, so `request.user` may still
        # be anonymous here; the DRF-level resolution happens again in
        # `apps.common.authentication.resolve_organization` for API calls.
        from apps.organizations.models import OrganizationMembership

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
            membership = membership_qs.filter(
                organization_id=user.active_organization_id
            ).first()
        if membership is None:
            membership = membership_qs.first()

        if membership is not None:
            request.organization = membership.organization
            request.membership = membership
            set_current_organization(membership.organization)
        elif user.is_superuser and requested_id:
            from apps.organizations.models import Organization

            organization = Organization.objects.filter(id=requested_id).first()
            request.organization = organization
            set_current_organization(organization)

        set_current_user(user)
        return None


class AuditLogMiddleware(MiddlewareMixin):
    """Record authentication events and data exports at the HTTP boundary.

    Per-object CRUD auditing is handled by :class:`apps.common.mixins.AuditMixin`;
    this middleware captures things that never reach a ViewSet.
    """

    AUDITED_PATHS = {
        "/api/v1/auth/login/": AuditAction.LOGIN,
        "/api/v1/auth/logout/": AuditAction.LOGOUT,
        "/api/v1/auth/password/change/": AuditAction.PASSWORD_CHANGE,
    }

    def process_response(self, request, response):
        path = request.path
        action = self.AUDITED_PATHS.get(path)

        if action is None and "/export" in path and request.method in {"GET", "POST"}:
            action = AuditAction.EXPORT

        if action is None:
            return response

        if action == AuditAction.LOGIN and response.status_code >= 400:
            action = AuditAction.LOGIN_FAILED

        try:
            from .services import AuditService

            AuditService.log(
                action=action,
                resource_type="auth" if "auth" in path else "export",
                resource_repr=path,
                metadata={"status_code": response.status_code},
                request=request,
                actor=getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
                organization=getattr(request, "organization", None),
            )
        except Exception:  # pragma: no cover - auditing must not break responses
            logger.exception("Audit middleware failed for %s", path)

        return response
