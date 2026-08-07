"""Authentication models: the user account and its security artefacts."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.timezone import now as _django_now
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.common.utils import generate_token, gravatar_url, initials, upload_to_path
from apps.common.validators import phone_validator

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """Platform user.

    A user is global (one account, one password) but participates in one or more
    organizations through :class:`apps.organizations.models.OrganizationMembership`.
    ``active_organization`` records the tenant the user last worked in.
    """

    class Theme(models.TextChoices):
        LIGHT = "light", _("Light")
        DARK = "dark", _("Dark")
        SYSTEM = "system", _("Follow system")

    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100, blank=True)
    phone = models.CharField(
        _("phone"), max_length=32, blank=True, validators=[phone_validator]
    )
    job_title = models.CharField(_("job title"), max_length=120, blank=True)
    bio = models.TextField(_("bio"), blank=True, max_length=1000)
    avatar = models.ImageField(_("avatar"), upload_to=upload_to_path, blank=True, null=True)

    # ---- Status flags ----
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_email_verified = models.BooleanField(_("email verified"), default=False)
    two_factor_enabled = models.BooleanField(_("two-factor enabled"), default=False)

    # ---- Preferences ----
    timezone = models.CharField(_("timezone"), max_length=64, default="UTC")
    language = models.CharField(_("language"), max_length=10, default="en")
    theme = models.CharField(
        _("theme"), max_length=10, choices=Theme.choices, default=Theme.SYSTEM
    )

    # ---- Tenancy ----
    active_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_users",
        verbose_name=_("active organization"),
    )

    # ---- Telemetry ----
    date_joined = models.DateTimeField(_("date joined"), default=_django_now)
    last_login_ip = models.GenericIPAddressField(_("last login IP"), null=True, blank=True)
    login_count = models.PositiveIntegerField(_("login count"), default=0)
    last_active_at = models.DateTimeField(_("last active"), null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    objects = UserManager()
    all_objects = UserManager(with_deleted=True)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def __str__(self) -> str:
        return self.full_name or self.email

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self) -> str:
        return self.full_name or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email.split("@")[0]

    @property
    def initials(self) -> str:
        return initials(self.first_name, self.last_name or self.email)

    @property
    def avatar_url(self) -> str:
        if self.avatar:
            return self.avatar.url
        return gravatar_url(self.email)

    # ------------------------------------------------------------------
    # Tenancy helpers
    # ------------------------------------------------------------------
    def organizations(self):
        """Every organization this user actively belongs to."""
        from apps.organizations.models import Organization

        return Organization.objects.filter(
            memberships__user=self, memberships__is_active=True
        ).distinct()

    def membership_for(self, organization):
        from apps.organizations.models import OrganizationMembership

        organization_id = getattr(organization, "id", organization)
        return OrganizationMembership.objects.filter(
            user=self, organization_id=organization_id, is_active=True
        ).first()

    def role_in(self, organization) -> str | None:
        membership = self.membership_for(organization)
        return membership.role if membership else None

    def has_capability(self, capability: str, organization=None) -> bool:
        """Check a fine-grained capability such as ``deals.delete``.

        Capabilities come from :class:`apps.users.models.Role` objects assigned
        to the user within the organization. Owners and admins short-circuit to
        ``True``.
        """
        from apps.common.constants import ROLE_HIERARCHY, OrganizationRole

        if self.is_superuser:
            return True

        organization = organization or self.active_organization
        if organization is None:
            return False

        membership = self.membership_for(organization)
        if membership is None:
            return False
        if ROLE_HIERARCHY.get(membership.role, 0) >= ROLE_HIERARCHY[OrganizationRole.ADMIN]:
            return True

        try:
            from apps.users.models import Role
        except ImportError:
            # The fine-grained capability app is not installed; the role
            # hierarchy checked above is the whole permission model.
            return False

        roles = Role.objects.filter(
            organization=organization, assignments__user=self, assignments__is_active=True
        )
        for role in roles:
            if capability in (role.capabilities or []):
                return True
            # Wildcards: "deals.*" grants every deals capability.
            prefix = capability.split(".")[0]
            if f"{prefix}.*" in (role.capabilities or []):
                return True
        return False

    def touch_last_active(self) -> None:
        self.last_active_at = timezone.now()
        self.save(update_fields=["last_active_at"])


class TokenBase(BaseModel):
    """Shared behaviour for single-use, time-limited tokens."""

    token = models.CharField(_("token"), max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField(_("expires at"))
    used_at = models.DateTimeField(_("used at"), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_used

    def consume(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])


class EmailVerificationToken(TokenBase):
    """Emailed to a new user to confirm ownership of their address."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
        verbose_name=_("user"),
    )
    email = models.EmailField(_("email"))

    class Meta(TokenBase.Meta):
        verbose_name = _("email verification token")
        verbose_name_plural = _("email verification tokens")

    def __str__(self) -> str:
        return f"Verification for {self.email}"

    @classmethod
    def issue(cls, user, ip_address: str | None = None) -> "EmailVerificationToken":
        ttl = getattr(settings, "EMAIL_VERIFICATION_TOKEN_TTL_HOURS", 48)
        # Invalidate any outstanding tokens for this user.
        cls.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        return cls.objects.create(
            user=user,
            email=user.email,
            token=generate_token(64),
            expires_at=timezone.now() + timedelta(hours=ttl),
            ip_address=ip_address,
        )


class PasswordResetToken(TokenBase):
    """Emailed when a user requests a password reset."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name=_("user"),
    )

    class Meta(TokenBase.Meta):
        verbose_name = _("password reset token")
        verbose_name_plural = _("password reset tokens")

    def __str__(self) -> str:
        return f"Password reset for {self.user_id}"

    @classmethod
    def issue(cls, user, ip_address: str | None = None) -> "PasswordResetToken":
        ttl = getattr(settings, "PASSWORD_RESET_TOKEN_TTL_HOURS", 2)
        cls.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        return cls.objects.create(
            user=user,
            token=generate_token(64),
            expires_at=timezone.now() + timedelta(hours=ttl),
            ip_address=ip_address,
        )


class SocialAccount(BaseModel):
    """Link between a NexusCRM user and an external identity provider."""

    class Provider(models.TextChoices):
        GOOGLE = "google", _("Google")
        MICROSOFT = "microsoft", _("Microsoft")
        GITHUB = "github", _("GitHub")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
        verbose_name=_("user"),
    )
    provider = models.CharField(_("provider"), max_length=32, choices=Provider.choices)
    provider_user_id = models.CharField(_("provider user id"), max_length=255)
    email = models.EmailField(_("email"), blank=True)
    extra_data = models.JSONField(_("extra data"), default=dict, blank=True)
    last_used_at = models.DateTimeField(_("last used"), null=True, blank=True)

    class Meta:
        verbose_name = _("social account")
        verbose_name_plural = _("social accounts")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"], name="uniq_social_identity"
            )
        ]
        indexes = [models.Index(fields=["user", "provider"])]

    def __str__(self) -> str:
        return f"{self.get_provider_display()}:{self.email or self.provider_user_id}"


class LoginAttempt(BaseModel):
    """Rate-limiting and forensics for authentication attempts."""

    email = models.EmailField(_("email"), db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_attempts",
    )
    succeeded = models.BooleanField(_("succeeded"), default=False)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    failure_reason = models.CharField(_("failure reason"), max_length=120, blank=True)

    class Meta:
        verbose_name = _("login attempt")
        verbose_name_plural = _("login attempts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "-created_at"]),
            models.Index(fields=["ip_address", "-created_at"]),
        ]

    def __str__(self) -> str:
        outcome = "success" if self.succeeded else "failure"
        return f"{self.email} {outcome} at {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def recent_failures(cls, email: str, minutes: int = 15) -> int:
        cutoff = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            email__iexact=email, succeeded=False, created_at__gte=cutoff
        ).count()


class UserSession(BaseModel):
    """Tracked refresh-token sessions so users can revoke devices."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name=_("user"),
    )
    jti = models.CharField(_("token id"), max_length=64, unique=True, db_index=True)
    device = models.CharField(_("device"), max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    expires_at = models.DateTimeField(_("expires at"))
    revoked_at = models.DateTimeField(_("revoked at"), null=True, blank=True)
    last_seen_at = models.DateTimeField(_("last seen"), default=timezone.now)

    class Meta:
        verbose_name = _("user session")
        verbose_name_plural = _("user sessions")
        ordering = ["-last_seen_at"]
        indexes = [models.Index(fields=["user", "-last_seen_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.device or 'unknown device'}"

    @property
    def is_active_session(self) -> bool:
        return self.revoked_at is None and timezone.now() < self.expires_at

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])


def default_uuid() -> str:
    """Helper kept for migration compatibility."""
    return str(uuid.uuid4())
