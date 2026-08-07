"""JWT authentication for Django Channels WebSocket connections.

Browsers cannot set custom headers on a WebSocket handshake, so the access token
is passed as a query parameter::

    ws://host/ws/notifications/?token=<access_token>&organization=<uuid>
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.sessions import CookieMiddleware, SessionMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_from_token(raw_token: str):
    """Validate a JWT access token and return the matching user."""
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    User = get_user_model()
    try:
        token = AccessToken(raw_token)
        user_id = token.get("user_id")
    except (InvalidToken, TokenError, KeyError) as exc:
        logger.debug("Rejected websocket token: %s", exc)
        return AnonymousUser()

    user = User.objects.filter(id=user_id, is_active=True).first()
    return user or AnonymousUser()


@database_sync_to_async
def _get_membership(user, organization_id: str | None):
    """Resolve the tenant for the socket, mirroring the HTTP middleware."""
    if user is None or isinstance(user, AnonymousUser):
        return None, None

    from apps.organizations.models import OrganizationMembership

    queryset = (
        OrganizationMembership.objects.filter(user=user, is_active=True)
        .select_related("organization")
        .order_by("created_at")
    )
    membership = None
    if organization_id:
        membership = queryset.filter(organization_id=organization_id).first()
    if membership is None and getattr(user, "active_organization_id", None):
        membership = queryset.filter(organization_id=user.active_organization_id).first()
    if membership is None:
        membership = queryset.first()

    if membership is None:
        return None, None
    return membership.organization, membership


class JWTAuthMiddleware(BaseMiddleware):
    """Populate ``scope['user']``, ``scope['organization']``, ``scope['membership']``."""

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)

        raw_token = None
        if "token" in params:
            raw_token = params["token"][0]
        else:
            for name, value in scope.get("headers", []):
                if name == b"authorization":
                    header = value.decode()
                    if header.lower().startswith("bearer "):
                        raw_token = header.split(" ", 1)[1]
                    break

        user = await _get_user_from_token(raw_token) if raw_token else AnonymousUser()
        scope["user"] = user

        organization_id = params.get("organization", [None])[0]
        organization, membership = await _get_membership(user, organization_id)
        scope["organization"] = organization
        scope["membership"] = membership

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):  # noqa: N802 - mirrors Channels' naming
    """Cookie + session + JWT stack, in the order Channels expects."""
    return CookieMiddleware(SessionMiddleware(JWTAuthMiddleware(inner)))
