"""Transactional emails for the authentication flows."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)
User = get_user_model()


def _send(subject: str, template: str, context: dict, recipient: str) -> bool:
    """Render an HTML email plus plain-text fallback and send it."""
    from django.core.mail import EmailMultiAlternatives

    context = {
        "site_name": "NexusCRM",
        "frontend_url": settings.FRONTEND_URL,
        "support_email": settings.DEFAULT_FROM_EMAIL,
        **context,
    }
    html_body = render_to_string(template, context)
    text_body = strip_tags(html_body)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    sent = message.send(fail_silently=False)
    logger.info("Sent '%s' to %s", subject, recipient)
    return bool(sent)


@shared_task(name="apps.accounts.tasks.send_verification_email", bind=True, max_retries=3)
def send_verification_email(self, user_id: str, token: str) -> bool:
    user = User.all_objects.filter(id=user_id).first()
    if user is None:
        logger.warning("Verification email skipped: user %s not found", user_id)
        return False

    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    try:
        return _send(
            subject="Verify your NexusCRM email address",
            template="emails/verify_email.html",
            context={"user": user, "verify_url": verify_url, "token": token},
            recipient=user.email,
        )
    except Exception as exc:  # pragma: no cover - SMTP failure
        logger.error("Verification email failed for %s: %s", user.email, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from exc


@shared_task(name="apps.accounts.tasks.send_password_reset_email", bind=True, max_retries=3)
def send_password_reset_email(self, user_id: str, token: str) -> bool:
    user = User.all_objects.filter(id=user_id).first()
    if user is None:
        return False

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    ttl_hours = getattr(settings, "PASSWORD_RESET_TOKEN_TTL_HOURS", 2)
    try:
        return _send(
            subject="Reset your NexusCRM password",
            template="emails/reset_password.html",
            context={"user": user, "reset_url": reset_url, "ttl_hours": ttl_hours},
            recipient=user.email,
        )
    except Exception as exc:  # pragma: no cover - SMTP failure
        logger.error("Password reset email failed for %s: %s", user.email, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from exc


@shared_task(name="apps.accounts.tasks.send_password_changed_email")
def send_password_changed_email(user_id: str) -> bool:
    user = User.all_objects.filter(id=user_id).first()
    if user is None:
        return False
    try:
        return _send(
            subject="Your NexusCRM password was changed",
            template="emails/password_changed.html",
            context={"user": user},
            recipient=user.email,
        )
    except Exception as exc:  # pragma: no cover - SMTP failure
        logger.error("Password-changed notice failed for %s: %s", user.email, exc)
        return False


@shared_task(name="apps.accounts.tasks.send_welcome_email")
def send_welcome_email(user_id: str, organization_name: str = "") -> bool:
    user = User.all_objects.filter(id=user_id).first()
    if user is None:
        return False
    try:
        return _send(
            subject="Welcome to NexusCRM",
            template="emails/welcome.html",
            context={"user": user, "organization_name": organization_name},
            recipient=user.email,
        )
    except Exception as exc:  # pragma: no cover - SMTP failure
        logger.error("Welcome email failed for %s: %s", user.email, exc)
        return False


@shared_task(name="apps.accounts.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> int:
    """Housekeeping: drop long-expired verification and reset tokens."""
    from .services import ProfileService

    removed = ProfileService().cleanup_expired_tokens()
    logger.info("Removed %s expired auth tokens", removed)
    return removed


@shared_task(name="apps.accounts.tasks.prune_login_attempts")
def prune_login_attempts(days: int = 30) -> int:
    """Drop login telemetry beyond the retention window."""
    from datetime import timedelta

    from django.utils import timezone

    from .models import LoginAttempt

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = LoginAttempt.all_objects.filter(created_at__lt=cutoff).delete()
    return deleted
