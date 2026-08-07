"""Managers for the custom user model."""
from __future__ import annotations

from django.contrib.auth.models import BaseUserManager
from django.db import models

from apps.common.utils import normalise_email


class UserQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, is_deleted=False)

    def verified(self):
        return self.filter(is_email_verified=True)

    def in_organization(self, organization):
        organization_id = getattr(organization, "id", organization)
        return self.filter(
            memberships__organization_id=organization_id, memberships__is_active=True
        ).distinct()

    def delete(self):  # type: ignore[override]
        from django.utils import timezone

        return self.update(is_deleted=True, deleted_at=timezone.now(), is_active=False)

    def hard_delete(self):
        return super().delete()


class UserManager(BaseUserManager):
    """Email-based user manager that also hides soft-deleted accounts."""

    use_in_migrations = True

    def __init__(self, *args, with_deleted: bool = False, **kwargs):
        self.with_deleted = with_deleted
        super().__init__(*args, **kwargs)

    def get_queryset(self) -> UserQuerySet:
        queryset = UserQuerySet(self.model, using=self._db)
        return queryset if self.with_deleted else queryset.filter(is_deleted=False)

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = normalise_email(self.normalize_email(email))
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["created_by", "updated_by", "deleted_by", "active_organization"])
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def get_by_natural_key(self, username: str):
        return self.get(email__iexact=normalise_email(username))

    def active(self):
        return self.get_queryset().active()

    def verified(self):
        return self.get_queryset().verified()

    def in_organization(self, organization):
        return self.get_queryset().in_organization(organization)
