"""Background jobs for the organizations app."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name="apps.organizations.tasks.send_invitation_email", bind=True, max_retries=3)
def send_invitation_email(self, invitation_id: str) -> bool:
    """Email the invitation link to the invitee."""
    from apps.accounts.tasks import _send

    from .models import Invitation

    invitation = (
        Invitation.objects.filter(id=invitation_id)
        .select_related("organization", "invited_by")
        .first()
    )
    if invitation is None:
        logger.warning("Invitation %s no longer exists", invitation_id)
        return False

    accept_url = f"{settings.FRONTEND_URL}/accept-invitation?token={invitation.token}"
    inviter_name = str(invitation.invited_by) if invitation.invited_by else "A teammate"

    try:
        return _send(
            subject=f"{inviter_name} invited you to {invitation.organization.name}",
            template="emails/invitation.html",
            context={
                "organization": invitation.organization,
                "inviter_name": inviter_name,
                "role_display": invitation.get_role_display(),
                "message": invitation.message,
                "accept_url": accept_url,
                "expires_at": invitation.expires_at,
            },
            recipient=invitation.email,
        )
    except Exception as exc:  # pragma: no cover - SMTP failure
        logger.error("Invitation email failed for %s: %s", invitation.email, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from exc


@shared_task(name="apps.organizations.tasks.expire_stale_invitations")
def expire_stale_invitations() -> int:
    """Mark invitations past their expiry date as expired."""
    from .repositories import InvitationRepository

    expired = InvitationRepository().expire_stale()
    if expired:
        logger.info("Expired %s stale invitations", expired)
    return expired


@shared_task(name="apps.organizations.tasks.notify_trial_expiring")
def notify_trial_expiring(days_before: int = 3) -> int:
    """Warn owners whose trial ends soon."""
    from datetime import timedelta

    from django.utils import timezone

    try:
        from apps.notifications.services import NotificationService
    except ImportError:
        logger.info("Notifications app not installed; skipping trial reminders")
        return 0

    from .models import Organization

    window_start = timezone.now()
    window_end = window_start + timedelta(days=days_before)

    organizations = Organization.objects.filter(
        trial_ends_at__gt=window_start, trial_ends_at__lte=window_end, is_active=True
    ).select_related("owner")

    notified = 0
    for organization in organizations:
        if organization.owner is None:
            continue
        NotificationService().notify(
            organization=organization,
            recipient=organization.owner,
            title="Your trial is ending soon",
            body=(
                f"The {organization.name} trial ends on "
                f"{organization.trial_ends_at:%d %B %Y}. Upgrade to keep full access."
            ),
            category="billing",
            action_url="/settings/billing",
        )
        notified += 1

    return notified


@shared_task(name="apps.organizations.tasks.recalculate_seat_usage")
def recalculate_seat_usage() -> dict:
    """Deactivate memberships that exceed a downgraded plan's seat limit."""
    from .models import Organization, OrganizationMembership

    adjusted: dict[str, int] = {}
    for organization in Organization.objects.filter(is_active=True):
        active = OrganizationMembership.objects.filter(
            organization=organization, is_active=True
        ).order_by("created_at")
        overage = active.count() - organization.max_users
        if overage <= 0:
            continue
        # Never deactivate owners or admins.
        candidates = list(
            active.exclude(role__in=["owner", "admin"]).order_by("-created_at")[:overage]
        )
        for membership in candidates:
            membership.is_active = False
            membership.save(update_fields=["is_active", "updated_at"])
        if candidates:
            adjusted[organization.slug] = len(candidates)

    if adjusted:
        logger.warning("Seat overage adjustments: %s", adjusted)
    return adjusted
