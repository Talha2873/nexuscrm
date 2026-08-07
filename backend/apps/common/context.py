"""Thread-local request context.

Signals, repositories and model ``save()`` hooks all need to know *who* is acting
and *which tenant* they are acting for, but they receive no ``request`` object.
This module stores that information for the lifetime of a request (set by
``apps.common.middleware.CurrentRequestMiddleware`` / ``OrganizationMiddleware``)
and clears it afterwards so nothing leaks between requests on a reused thread.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any

_state = threading.local()


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------
def set_current_request(request: Any | None) -> None:
    _state.request = request


def get_current_request() -> Any | None:
    return getattr(_state, "request", None)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
def set_current_user(user: Any | None) -> None:
    _state.user = user


def get_current_user() -> Any | None:
    """Return the authenticated user, or ``None`` for anonymous/system calls."""
    user = getattr(_state, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


# ---------------------------------------------------------------------------
# Organization (tenant)
# ---------------------------------------------------------------------------
def set_current_organization(organization: Any | None) -> None:
    _state.organization = organization


def get_current_organization() -> Any | None:
    return getattr(_state, "organization", None)


def get_current_organization_id() -> Any | None:
    organization = get_current_organization()
    return getattr(organization, "id", None)


# ---------------------------------------------------------------------------
# Request ID (correlation)
# ---------------------------------------------------------------------------
def set_request_id(request_id: str | None) -> None:
    _state.request_id = request_id


def get_request_id() -> str | None:
    return getattr(_state, "request_id", None)


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------
def clear_current_context() -> None:
    """Drop every value held for the current thread."""
    for attribute in ("request", "user", "organization", "request_id"):
        if hasattr(_state, attribute):
            delattr(_state, attribute)


@contextmanager
def tenant_context(organization: Any | None = None, user: Any | None = None):
    """Temporarily act as ``user`` inside ``organization``.

    Used by Celery tasks, management commands and tests, which have no request::

        with tenant_context(organization=org, user=system_user):
            DealService().create(payload)
    """
    previous_org = get_current_organization()
    previous_user = get_current_user()
    set_current_organization(organization)
    set_current_user(user)
    try:
        yield
    finally:
        set_current_organization(previous_org)
        set_current_user(previous_user)
