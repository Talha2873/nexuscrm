"""Signal receivers for the accounts app."""
from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.common.utils import normalise_email

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def normalise_user_email(sender, instance, **kwargs):
    """Store every address in a canonical lowercase-domain form."""
    if instance.email:
        instance.email = normalise_email(instance.email)


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def reset_verification_on_email_change(sender, instance, **kwargs):
    """Changing an email address invalidates its verified status."""
    if not instance.pk:
        return
    previous = sender.all_objects.filter(pk=instance.pk).only("email").first()
    if previous and previous.email != instance.email:
        instance.is_email_verified = False


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Every user gets a preferences/profile row in the users app."""
    if not created:
        return
    try:
        from apps.users.models import UserProfile

        UserProfile.objects.get_or_create(user=instance)
    except Exception:  # pragma: no cover - app may be migrating
        logger.exception("Could not create profile for user %s", instance.pk)
