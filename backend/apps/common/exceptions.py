"""Domain exceptions and the unified DRF error envelope.

Every error the API returns has the same shape, so the frontend needs exactly
one error handler::

    {
      "success": false,
      "error": {
        "code": "validation_error",
        "message": "Validation failed.",
        "details": {"email": ["This field is required."]}
      },
      "request_id": "1f0c..."
    }
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .context import get_request_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application exceptions
# ---------------------------------------------------------------------------
class ServiceError(APIException):
    """Base class for business-rule violations raised by the service layer."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be completed."
    default_code = "service_error"

    def __init__(self, detail: Any = None, code: str | None = None, details: Any = None):
        super().__init__(detail or self.default_detail, code or self.default_code)
        self.extra_details = details or {}


class BusinessRuleViolation(ServiceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "This action violates a business rule."
    default_code = "business_rule_violation"


class ResourceNotFound(ServiceError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class DuplicateResource(ServiceError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A record with these details already exists."
    default_code = "duplicate_resource"


class OrganizationRequired(ServiceError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "No active organization selected for this request."
    default_code = "organization_required"


class PermissionDeniedError(ServiceError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class ExternalServiceError(ServiceError):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "An upstream service is currently unavailable."
    default_code = "external_service_error"


class AIServiceError(ExternalServiceError):
    default_detail = "The AI assistant is temporarily unavailable."
    default_code = "ai_service_error"


class RateLimitExceeded(ServiceError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests. Please slow down."
    default_code = "rate_limit_exceeded"


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------
def _normalise_detail(detail: Any) -> tuple[str, Any]:
    """Split a DRF detail structure into (message, details)."""
    if isinstance(detail, dict):
        first_key = next(iter(detail), None)
        first_value = detail.get(first_key) if first_key else None
        if isinstance(first_value, (list, tuple)) and first_value:
            message = str(first_value[0])
        else:
            message = str(first_value) if first_value is not None else "Validation failed."
        return message, detail
    if isinstance(detail, (list, tuple)):
        message = str(detail[0]) if detail else "Validation failed."
        return message, {"non_field_errors": [str(item) for item in detail]}
    return str(detail), {}


def custom_exception_handler(exc, context) -> Response | None:
    """Wrap every error in the standard envelope."""
    # Translate Django-native exceptions into DRF ones first.
    if isinstance(exc, DjangoValidationError):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        exc = DRFValidationError(detail=getattr(exc, "message_dict", None) or exc.messages)
    elif isinstance(exc, ObjectDoesNotExist):
        exc = ResourceNotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDeniedError()
    elif isinstance(exc, IntegrityError):
        logger.warning("Integrity error: %s", exc)
        exc = DuplicateResource(
            detail="This operation conflicts with an existing record."
        )

    response = drf_exception_handler(exc, context)
    request = context.get("request")
    view = context.get("view")

    if response is None:
        # Unhandled exception: log it and return a safe 500.
        logger.exception(
            "Unhandled exception in %s: %s",
            getattr(view, "__class__", type(view)).__name__,
            exc,
        )
        return Response(
            {
                "success": False,
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again.",
                    "details": {},
                },
                "request_id": get_request_id(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    message, details = _normalise_detail(response.data)
    code = getattr(exc, "default_code", "error")
    if isinstance(exc, APIException) and isinstance(exc.detail, (str, list, dict)):
        code = getattr(exc.detail, "code", code) or code
    if isinstance(exc, Http404):
        code = "not_found"

    extra = getattr(exc, "extra_details", None)
    if extra:
        details = {**details, **extra}

    response.data = {
        "success": False,
        "error": {"code": str(code), "message": message, "details": details},
        "request_id": get_request_id(),
    }

    if response.status_code >= 500:
        logger.error("Server error %s: %s", response.status_code, message)
    elif request is not None and response.status_code in (401, 403):
        logger.info(
            "Access denied (%s) for %s %s",
            response.status_code,
            request.method,
            request.path,
        )

    return response
