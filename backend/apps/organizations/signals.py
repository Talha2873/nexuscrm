"""Signal receivers for the organizations app."""
from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Organization, OrganizationMembership, OrganizationSettings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Organization)
def create_organization_settings(sender, instance, created, **kwargs):
    """Every tenant gets a settings row the moment it exists."""
    if not created:
        return
    OrganizationSettings.objects.get_or_create(
        organization=instance,
        defaults={"working_days": OrganizationSettings.default_working_days()},
    )


@receiver(pre_save, sender=Organization)
def ensure_organization_slug(sender, instance, **kwargs):
    """Guarantee a unique slug even when one is set manually."""
    if instance.slug:
        return
    from apps.common.utils import unique_slugify

    instance.slug = unique_slugify(instance, instance.name)


@receiver(post_save, sender=OrganizationMembership)
def set_active_organization_on_first_membership(sender, instance, created, **kwargs):
    """A user's first organization becomes their active one automatically."""
    if not created or not instance.is_active:
        return
    user = instance.user
    if user.active_organization_id is None:
        user.active_organization = instance.organization
        user.save(update_fields=["active_organization", "updated_at"])


@receiver(post_save, sender=OrganizationMembership)
def notify_on_new_member(sender, instance, created, **kwargs):
    """Tell the organization's admins when someone joins."""
    if not created or not instance.is_active:
        return
    try:
        from apps.notifications.tasks import notify_organization_admins

        notify_organization_admins.delay(
            organization_id=str(instance.organization_id),
            title="A new member joined",
            body=f"{instance.user} joined as {instance.get_role_display()}.",
            category="organization",
            action_url="/settings/members",
            exclude_user_id=str(instance.user_id),
        )
    except Exception:  # pragma: no cover - notifications must not block signup
        logger.exception("Could not queue new-member notification")
