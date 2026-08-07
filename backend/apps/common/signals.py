"""Signal receivers owned by the common app."""
from __future__ import annotations

import logging

from django.contrib.auth import user_logged_in, user_login_failed
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .constants import AuditAction
from .context import get_current_request
from .models import Document

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def record_successful_login(sender, request, user, **kwargs):
    """Audit successful logins and bump the user's login counters."""
    from .services import AuditService

    AuditService.log(
        action=AuditAction.LOGIN,
        resource_type="accounts.User",
        resource_id=user.pk,
        resource_repr=user.email,
        actor=user,
        request=request,
    )

    update_fields = []
    if hasattr(user, "login_count"):
        user.login_count = (user.login_count or 0) + 1
        update_fields.append("login_count")
    if hasattr(user, "last_login_ip") and request is not None:
        from .utils import get_client_ip

        user.last_login_ip = get_client_ip(request)
        update_fields.append("last_login_ip")
    if update_fields:
        user.save(update_fields=update_fields)


@receiver(user_login_failed)
def record_failed_login(sender, credentials, request=None, **kwargs):
    """Audit failed logins without ever storing the attempted password."""
    from .services import AuditService

    AuditService.log(
        action=AuditAction.LOGIN_FAILED,
        resource_type="accounts.User",
        resource_repr=str(credentials.get("username") or credentials.get("email") or ""),
        metadata={"reason": "invalid_credentials"},
        request=request or get_current_request(),
    )


@receiver(pre_save, sender=Document)
def stamp_document_metadata(sender, instance, **kwargs):
    """Keep file size / MIME type in sync when a file is replaced."""
    if not instance.pk or not instance.file:
        return
    previous = Document.all_objects.filter(pk=instance.pk).only("file").first()
    if previous and previous.file and previous.file.name != instance.file.name:
        from .utils import guess_mime_type

        instance.version = (instance.version or 1) + 1
        instance.mime_type = guess_mime_type(instance.file.name)
        try:
            instance.file_size = instance.file.size
        except (OSError, ValueError):
            pass


@receiver(post_delete, sender=Document)
def delete_document_file(sender, instance, **kwargs):
    """Remove the blob from storage when a document is hard-deleted."""
    if instance.file:
        try:
            instance.file.delete(save=False)
        except Exception:  # pragma: no cover - storage backend failure
            logger.warning("Could not delete file for document %s", instance.pk)
