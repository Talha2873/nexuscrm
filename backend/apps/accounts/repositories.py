"""Persistence gateways for authentication models."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.common.repositories import BaseRepository
from apps.common.utils import normalise_email

from .models import (
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    SocialAccount,
    UserSession,
)

User = get_user_model()


class UserRepository(BaseRepository):
    """Users are global, not tenant-scoped, so reads bypass organization filtering."""

    model = User
    select_related = ("active_organization",)
    default_ordering = ("first_name", "last_name")

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def get_by_email(self, email: str, include_deleted: bool = False):
        return (
            self.get_queryset(include_deleted=include_deleted)
            .filter(email__iexact=normalise_email(email))
            .first()
        )

    def email_exists(self, email: str) -> bool:
        return User.all_objects.filter(email__iexact=normalise_email(email)).exists()

    def create_user(self, email: str, password: str | None = None, **extra):
        return User.objects.create_user(email=email, password=password, **extra)

    def in_organization(self, organization):
        return User.objects.in_organization(organization).select_related("active_organization")

    def set_active_organization(self, user, organization):
        user.active_organization = organization
        user.save(update_fields=["active_organization", "updated_at"])
        return user

    def mark_email_verified(self, user):
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])
        return user

    def set_password(self, user, raw_password: str):
        user.set_password(raw_password)
        user.save(update_fields=["password", "updated_at"])
        return user


class EmailVerificationTokenRepository(BaseRepository):
    model = EmailVerificationToken
    select_related = ("user",)

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def get_valid(self, token: str):
        instance = self.get_queryset().filter(token=token).first()
        return instance if instance and instance.is_valid else None


class PasswordResetTokenRepository(BaseRepository):
    model = PasswordResetToken
    select_related = ("user",)

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def get_valid(self, token: str):
        instance = self.get_queryset().filter(token=token).first()
        return instance if instance and instance.is_valid else None


class SocialAccountRepository(BaseRepository):
    model = SocialAccount
    select_related = ("user",)

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def get_for_provider(self, provider: str, provider_user_id: str):
        return self.get_queryset().filter(
            provider=provider, provider_user_id=provider_user_id
        ).first()

    def link(self, user, provider: str, provider_user_id: str, email: str, extra: dict):
        account, _created = SocialAccount.objects.update_or_create(
            provider=provider,
            provider_user_id=provider_user_id,
            defaults={
                "user": user,
                "email": email,
                "extra_data": extra,
                "last_used_at": timezone.now(),
            },
        )
        return account


class LoginAttemptRepository(BaseRepository):
    model = LoginAttempt

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def record(self, email: str, succeeded: bool, user=None, request=None, reason: str = ""):
        from apps.common.utils import get_client_ip, get_user_agent

        return LoginAttempt.objects.create(
            email=normalise_email(email),
            user=user,
            succeeded=succeeded,
            failure_reason=reason[:120],
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else "",
        )


class UserSessionRepository(BaseRepository):
    model = UserSession
    select_related = ("user",)
    default_ordering = ("-last_seen_at",)

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def active_for_user(self, user):
        return self.get_queryset().filter(
            user=user, revoked_at__isnull=True, expires_at__gt=timezone.now()
        )

    def revoke_all(self, user, except_jti: str | None = None) -> int:
        queryset = self.get_queryset().filter(user=user, revoked_at__isnull=True)
        if except_jti:
            queryset = queryset.exclude(jti=except_jti)
        return queryset.update(revoked_at=timezone.now())
