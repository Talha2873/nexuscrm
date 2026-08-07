"""Small helpers shared across apps."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import secrets
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable

from django.utils import timezone
from django.utils.text import slugify

from .constants import SENSITIVE_FIELDS


def generate_token(length: int = 48) -> str:
    """Cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(length)[:length]


def generate_reference(prefix: str, length: int = 8) -> str:
    """Human-friendly reference like ``INV-9F3A2C71``."""
    return f"{prefix.upper()}-{uuid.uuid4().hex[:length].upper()}"


def unique_slugify(instance, value: str, slug_field: str = "slug", queryset=None) -> str:
    """Return a slug for ``value`` that is unique for the model (per tenant)."""
    base = slugify(value)[:200] or uuid.uuid4().hex[:12]
    model = instance.__class__
    if queryset is None:
        manager = getattr(model, "all_objects", model._default_manager)
        queryset = manager.all()
        organization_id = getattr(instance, "organization_id", None)
        if organization_id is not None:
            queryset = queryset.filter(organization_id=organization_id)
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    slug = base
    suffix = 2
    while queryset.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def upload_to_path(instance, filename: str) -> str:
    """Namespace uploads per tenant, model and date to avoid collisions."""
    extension = os.path.splitext(filename)[1].lower()
    organization_id = getattr(instance, "organization_id", None) or "shared"
    model_name = instance.__class__.__name__.lower()
    today = timezone.now()
    return (
        f"{organization_id}/{model_name}/{today:%Y/%m}/"
        f"{uuid.uuid4().hex}{extension}"
    )


def guess_mime_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def human_file_size(num_bytes: int | None) -> str:
    if not num_bytes:
        return "0 B"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def mask_sensitive(payload: Any) -> Any:
    """Recursively replace secret-looking values with ``***``."""
    if isinstance(payload, dict):
        return {
            key: ("***" if key.lower() in SENSITIVE_FIELDS else mask_sensitive(value))
            for key, value in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [mask_sensitive(item) for item in payload]
    return payload


def serialise_value(value: Any) -> Any:
    """Convert model field values into JSON-safe primitives for audit logs."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return [serialise_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialise_value(item) for key, item in value.items()}
    return str(value)


def model_to_snapshot(instance, fields: Iterable[str] | None = None) -> dict[str, Any]:
    """JSON-safe snapshot of a model instance, used for audit diffing."""
    snapshot: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        if fields is not None and field.name not in fields:
            continue
        snapshot[field.name] = serialise_value(getattr(instance, field.attname, None))
    return mask_sensitive(snapshot)


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return ``{field: {"from": old, "to": new}}`` for changed fields only."""
    changes: dict[str, Any] = {}
    for key in set(before) | set(after):
        old, new = before.get(key), after.get(key)
        if old != new:
            changes[key] = {"from": old, "to": new}
    return changes


def get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


def date_range(start: date, end: date):
    """Yield every date from ``start`` to ``end`` inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def start_of_day(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        value = value.date()
    return timezone.make_aware(datetime.combine(value, datetime.min.time()))


def end_of_day(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        value = value.date()
    return timezone.make_aware(datetime.combine(value, datetime.max.time()))


def percentage_change(previous: float | Decimal | None, current: float | Decimal | None) -> float:
    """Percentage delta between two periods, guarding against division by zero."""
    previous = float(previous or 0)
    current = float(current or 0)
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


def gravatar_url(email: str, size: int = 200) -> str:
    digest = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    return f"https://www.gravatar.com/avatar/{digest}?s={size}&d=identicon"


def initials(*parts: str) -> str:
    letters = [part.strip()[0].upper() for part in parts if part and part.strip()]
    return "".join(letters[:2]) or "?"


def normalise_email(email: str) -> str:
    email = (email or "").strip()
    if "@" not in email:
        return email.lower()
    local, _, domain = email.partition("@")
    return f"{local}@{domain.lower()}"


def camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
