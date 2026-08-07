"""Reusable field validators."""
from __future__ import annotations

import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

#: E.164-ish phone numbers, optionally prefixed with '+'.
phone_validator = RegexValidator(
    regex=r"^\+?[0-9\s\-().]{7,20}$",
    message=_("Enter a valid phone number (7-20 digits, optional + prefix)."),
)

#: Lowercase slug used for organization sub-domains.
slug_validator = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    message=_("Use lowercase letters, numbers and single hyphens only."),
)

hex_color_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    message=_("Enter a valid hex colour, e.g. #2563eb."),
)


def validate_file_size(value) -> None:
    """Reject uploads larger than ``settings.MAX_UPLOAD_SIZE``."""
    limit = getattr(settings, "MAX_UPLOAD_SIZE", 25 * 1024 * 1024)
    if value.size > limit:
        raise ValidationError(
            _("File is too large. Maximum size is %(limit)s MB.")
            % {"limit": round(limit / (1024 * 1024))}
        )


def validate_file_extension(value) -> None:
    """Allow only extensions listed in ``settings.ALLOWED_UPLOAD_EXTENSIONS``."""
    allowed = [ext.lower() for ext in getattr(settings, "ALLOWED_UPLOAD_EXTENSIONS", [])]
    if not allowed:
        return
    extension = os.path.splitext(value.name)[1].lower()
    if extension not in allowed:
        raise ValidationError(
            _("Unsupported file type '%(ext)s'. Allowed: %(allowed)s.")
            % {"ext": extension or "unknown", "allowed": ", ".join(allowed)}
        )


def validate_strong_password(value: str) -> None:
    """Require a mix of character classes on top of Django's own validators."""
    errors = []
    if len(value) < 8:
        errors.append(_("at least 8 characters"))
    if not re.search(r"[A-Z]", value):
        errors.append(_("one uppercase letter"))
    if not re.search(r"[a-z]", value):
        errors.append(_("one lowercase letter"))
    if not re.search(r"[0-9]", value):
        errors.append(_("one digit"))
    if errors:
        raise ValidationError(
            _("Password must contain %(requirements)s.")
            % {"requirements": ", ".join(str(error) for error in errors)}
        )


def validate_non_negative(value) -> None:
    if value is not None and value < 0:
        raise ValidationError(_("This value cannot be negative."))


def validate_percentage(value) -> None:
    if value is not None and not (0 <= value <= 100):
        raise ValidationError(_("Enter a percentage between 0 and 100."))
