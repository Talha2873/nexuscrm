"""Abstract base models and the shared cross-cutting models.

Inheritance chain used by every domain model in NexusCRM::

    UUIDModel + TimeStampedModel + SoftDeleteModel  ->  BaseModel
    BaseModel + organization FK                     ->  TenantBaseModel
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .constants import ActivityVerb, AuditAction
from .context import get_current_user
from .managers import SoftDeleteManager, TenantManager
from .utils import guess_mime_type, upload_to_path
from .validators import (
    hex_color_validator,
    validate_file_extension,
    validate_file_size,
)


# ---------------------------------------------------------------------------
# Abstract bases
# ---------------------------------------------------------------------------
class UUIDModel(models.Model):
    """Primary keys are UUIDv4: safe to expose in URLs, mergeable across shards."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Rows are never really deleted, keeping history and audit trails intact."""

    is_deleted = models.BooleanField(_("deleted"), default=False, db_index=True)
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("deleted by"),
    )

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard: bool = False):  # type: ignore[override]
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.deleted_at = timezone.now()
        user = get_current_user()
        if user is not None:
            self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
        return (1, {self._meta.label: 1})

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """Every persisted domain object inherits from this."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("created by"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("updated by"),
    )

    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(with_deleted=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Stamp the acting user automatically when one is in context."""
        user = get_current_user()
        if user is not None:
            if self._state.adding and self.created_by_id is None:
                self.created_by = user
            update_fields = kwargs.get("update_fields")
            if update_fields is None or "updated_by" in update_fields:
                self.updated_by = user
        super().save(*args, **kwargs)


class TenantBaseModel(BaseModel):
    """Base class for every organization-scoped (multi-tenant) model."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        verbose_name=_("organization"),
        db_index=True,
    )

    objects = TenantManager()
    all_objects = TenantManager(with_deleted=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# Concrete shared models
# ---------------------------------------------------------------------------
class Tag(TenantBaseModel):
    """Free-form label attachable to any record via ``TaggedItem``."""

    name = models.CharField(_("name"), max_length=64)
    slug = models.SlugField(_("slug"), max_length=80)
    color = models.CharField(
        _("colour"), max_length=7, default="#2563eb", validators=[hex_color_validator]
    )
    description = models.CharField(_("description"), max_length=255, blank=True)

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(is_deleted=False),
                name="uniq_tag_slug_per_org",
            )
        ]
        indexes = [models.Index(fields=["organization", "name"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from .utils import unique_slugify

            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


class TaggedItem(TenantBaseModel):
    """Generic many-to-many bridge between :class:`Tag` and any model."""

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="tagged_items")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("tagged item")
        verbose_name_plural = _("tagged items")
        constraints = [
            models.UniqueConstraint(
                fields=["tag", "content_type", "object_id"],
                name="uniq_tag_per_object",
            )
        ]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self) -> str:
        return f"{self.tag.name} -> {self.content_type.model}:{self.object_id}"


class Document(TenantBaseModel):
    """Uploaded file, optionally attached to any record in the CRM."""

    class Category(models.TextChoices):
        CONTRACT = "contract", _("Contract")
        PROPOSAL = "proposal", _("Proposal")
        INVOICE = "invoice", _("Invoice")
        PRESENTATION = "presentation", _("Presentation")
        IMAGE = "image", _("Image")
        REPORT = "report", _("Report")
        OTHER = "other", _("Other")

    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    file = models.FileField(
        _("file"),
        upload_to=upload_to_path,
        validators=[validate_file_size, validate_file_extension],
    )
    category = models.CharField(
        _("category"), max_length=32, choices=Category.choices, default=Category.OTHER
    )
    file_size = models.PositiveBigIntegerField(_("file size"), default=0)
    mime_type = models.CharField(_("MIME type"), max_length=128, blank=True)
    is_public = models.BooleanField(_("shared with organization"), default=True)
    version = models.PositiveIntegerField(_("version"), default=1)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.UUIDField(null=True, blank=True, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
        verbose_name=_("uploaded by"),
    )

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("document")
        verbose_name_plural = _("documents")
        indexes = [
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):  # file not yet committed to storage
                self.file_size = 0
        if self.file and not self.mime_type:
            self.mime_type = guess_mime_type(self.file.name)
        if not self.name and self.file:
            self.name = self.file.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)

    @property
    def extension(self) -> str:
        return self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""


class Note(TenantBaseModel):
    """Free-text note pinned to any record (customer, deal, ticket, ...)."""

    body = models.TextField(_("body"))
    is_pinned = models.BooleanField(_("pinned"), default=False)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
        verbose_name=_("author"),
    )

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("note")
        verbose_name_plural = _("notes")
        ordering = ["-is_pinned", "-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self) -> str:
        return self.body[:60]


class Activity(TenantBaseModel):
    """Timeline entry: 'who did what to which record, and when'."""

    verb = models.CharField(_("verb"), max_length=32, choices=ActivityVerb.choices)
    description = models.CharField(_("description"), max_length=512)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("actor"),
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.UUIDField(null=True, blank=True, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    target_repr = models.CharField(_("target"), max_length=255, blank=True)

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.actor_id or 'system'} {self.verb} {self.target_repr}"


class AuditLog(BaseModel):
    """Immutable security/compliance record of every state change.

    Deliberately *not* tenant-scoped at the model level: platform staff must be
    able to audit actions that happen before an organization is resolved (failed
    logins, registrations). ``organization`` is therefore nullable.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("organization"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("actor"),
    )
    actor_email = models.EmailField(_("actor email"), blank=True)
    action = models.CharField(_("action"), max_length=32, choices=AuditAction.choices)
    resource_type = models.CharField(_("resource type"), max_length=128, blank=True)
    resource_id = models.CharField(_("resource id"), max_length=64, blank=True)
    resource_repr = models.CharField(_("resource"), max_length=255, blank=True)
    changes = models.JSONField(_("changes"), default=dict, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    request_id = models.CharField(_("request id"), max_length=64, blank=True, db_index=True)
    request_method = models.CharField(_("method"), max_length=10, blank=True)
    request_path = models.CharField(_("path"), max_length=512, blank=True)
    status_code = models.PositiveSmallIntegerField(_("status code"), null=True, blank=True)

    class Meta:
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.actor_email or 'anonymous'} {self.action} {self.resource_type}"
