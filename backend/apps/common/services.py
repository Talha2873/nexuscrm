"""Service layer.

Views stay thin: they validate input and delegate here. Services own the
business rules, coordinate repositories, emit activities/notifications and wrap
multi-step operations in transactions.
"""
from __future__ import annotations

import logging
from typing import Any, Generic, Sequence, TypeVar

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Model

from .constants import ActivityVerb
from .context import get_current_organization, get_current_user
from .exceptions import OrganizationRequired, ResourceNotFound
from .repositories import BaseRepository

ModelType = TypeVar("ModelType", bound=Model)

logger = logging.getLogger(__name__)


class BaseService(Generic[ModelType]):
    """Common CRUD orchestration with activity logging built in."""

    repository_class: type[BaseRepository]
    #: Human label used in timeline entries ("Deal", "Customer", ...).
    entity_name: str = "Record"
    #: Verbs recorded on the activity timeline for this entity.
    track_activity: bool = True

    def __init__(self, repository: BaseRepository | None = None) -> None:
        self.repository = repository or self.repository_class()

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    @property
    def organization(self):
        organization = get_current_organization()
        if organization is None:
            raise OrganizationRequired()
        return organization

    @property
    def current_user(self):
        return get_current_user()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def list(self, **filters: Any):
        return self.repository.filter(**filters) if filters else self.repository.all()

    def get(self, pk: Any) -> ModelType:
        instance = self.repository.get_by_id(pk)
        if instance is None:
            raise ResourceNotFound(f"{self.entity_name} not found.")
        return instance

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    @transaction.atomic
    def create(self, **payload: Any) -> ModelType:
        payload = self.before_create(payload)
        instance = self.repository.create(**payload)
        self.after_create(instance)
        self.log_activity(
            instance,
            ActivityVerb.CREATED,
            f"{self.entity_name} '{instance}' was created",
        )
        return instance

    @transaction.atomic
    def update(self, instance: ModelType, **payload: Any) -> ModelType:
        payload = self.before_update(instance, payload)
        instance = self.repository.update(instance, **payload)
        self.after_update(instance)
        self.log_activity(
            instance,
            ActivityVerb.UPDATED,
            f"{self.entity_name} '{instance}' was updated",
            metadata={"fields": sorted(payload.keys())},
        )
        return instance

    @transaction.atomic
    def delete(self, instance: ModelType, hard: bool = False) -> None:
        self.before_delete(instance)
        description = f"{self.entity_name} '{instance}' was deleted"
        self.repository.delete(instance, hard=hard)
        self.after_delete(instance)
        if not hard:
            self.log_activity(instance, ActivityVerb.DELETED, description)

    @transaction.atomic
    def restore(self, pk: Any) -> ModelType:
        instance = self.repository.get_by_id(pk, include_deleted=True)
        if instance is None:
            raise ResourceNotFound(f"{self.entity_name} not found.")
        return self.repository.restore(instance)

    @transaction.atomic
    def bulk_delete(self, ids: Sequence[Any], hard: bool = False) -> int:
        deleted = 0
        for pk in ids:
            instance = self.repository.get_by_id(pk)
            if instance is not None:
                self.delete(instance, hard=hard)
                deleted += 1
        return deleted

    # ------------------------------------------------------------------
    # Hooks - override in concrete services
    # ------------------------------------------------------------------
    def before_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def after_create(self, instance: ModelType) -> None:
        return None

    def before_update(self, instance: ModelType, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def after_update(self, instance: ModelType) -> None:
        return None

    def before_delete(self, instance: ModelType) -> None:
        return None

    def after_delete(self, instance: ModelType) -> None:
        return None

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------
    def log_activity(
        self,
        instance: Model,
        verb: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Append an entry to the organization's activity timeline."""
        if not self.track_activity:
            return None

        from .models import Activity

        organization = getattr(instance, "organization", None) or get_current_organization()
        if organization is None:
            return None

        try:
            return Activity.objects.create(
                organization=organization,
                actor=self.current_user,
                verb=verb,
                description=description[:512],
                metadata=metadata or {},
                content_type=ContentType.objects.get_for_model(instance.__class__),
                object_id=instance.pk,
                target_repr=str(instance)[:255],
            )
        except Exception:  # pragma: no cover - timeline must never break a write
            logger.exception("Failed to write activity for %s", instance)
            return None


class ActivityService:
    """Reads and writes the shared activity timeline."""

    @staticmethod
    def record(
        instance: Model,
        verb: str,
        description: str,
        actor=None,
        organization=None,
        metadata: dict[str, Any] | None = None,
    ):
        from .models import Activity

        organization = organization or getattr(instance, "organization", None) or get_current_organization()
        if organization is None:
            return None
        return Activity.objects.create(
            organization=organization,
            actor=actor or get_current_user(),
            verb=verb,
            description=description[:512],
            metadata=metadata or {},
            content_type=ContentType.objects.get_for_model(instance.__class__),
            object_id=instance.pk,
            target_repr=str(instance)[:255],
        )

    @staticmethod
    def for_object(instance: Model):
        from .models import Activity

        return Activity.objects.filter(
            content_type=ContentType.objects.get_for_model(instance.__class__),
            object_id=instance.pk,
        ).select_related("actor")


class AuditService:
    """Writes immutable audit records."""

    @staticmethod
    def log(
        action: str,
        resource_type: str = "",
        resource_id: Any = "",
        resource_repr: str = "",
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        actor=None,
        organization=None,
        request=None,
    ):
        from .models import AuditLog
        from .utils import get_client_ip, get_user_agent

        actor = actor or get_current_user()
        organization = organization or get_current_organization()

        payload: dict[str, Any] = {
            "organization": organization,
            "actor": actor,
            "actor_email": getattr(actor, "email", "") or "",
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id or ""),
            "resource_repr": resource_repr[:255],
            "changes": changes or {},
            "metadata": metadata or {},
        }

        if request is not None:
            payload.update(
                {
                    "ip_address": get_client_ip(request),
                    "user_agent": get_user_agent(request),
                    "request_method": request.method,
                    "request_path": request.path[:512],
                }
            )

        from .context import get_request_id

        payload["request_id"] = get_request_id() or ""

        try:
            return AuditLog.objects.create(**payload)
        except Exception:  # pragma: no cover - auditing must never break a request
            logger.exception("Failed to write audit log for action=%s", action)
            return None
