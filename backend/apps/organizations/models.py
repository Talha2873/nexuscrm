"""Tenant models.

An :class:`Organization` is the tenant boundary: every CRM record belongs to
exactly one. Users join organizations through :class:`OrganizationMembership`,
and can be grouped further into :class:`Team` and :class:`Department`.
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.constants import CompanySize, Currency, Industry, OrganizationRole
from apps.common.models import BaseModel, TenantBaseModel
from apps.common.utils import generate_token, unique_slugify, upload_to_path
from apps.common.validators import hex_color_validator, phone_validator, slug_validator


class Organization(BaseModel):
    """A tenant: a company using NexusCRM."""

    class Plan(models.TextChoices):
        FREE = "free", _("Free")
        STARTER = "starter", _("Starter")
        PROFESSIONAL = "professional", _("Professional")
        ENTERPRISE = "enterprise", _("Enterprise")

    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(
        _("slug"), max_length=255, unique=True, validators=[slug_validator]
    )
    legal_name = models.CharField(_("legal name"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True, max_length=2000)

    # ---- Branding ----
    logo = models.ImageField(_("logo"), upload_to=upload_to_path, blank=True, null=True)
    primary_color = models.CharField(
        _("primary colour"), max_length=7, default="#2563eb", validators=[hex_color_validator]
    )

    # ---- Profile ----
    industry = models.CharField(
        _("industry"), max_length=32, choices=Industry.choices, default=Industry.OTHER
    )
    company_size = models.CharField(
        _("company size"), max_length=16, choices=CompanySize.choices, default=CompanySize.SMALL
    )
    website = models.URLField(_("website"), blank=True)
    email = models.EmailField(_("contact email"), blank=True)
    phone = models.CharField(
        _("phone"), max_length=32, blank=True, validators=[phone_validator]
    )

    # ---- Address ----
    address_line1 = models.CharField(_("address line 1"), max_length=255, blank=True)
    address_line2 = models.CharField(_("address line 2"), max_length=255, blank=True)
    city = models.CharField(_("city"), max_length=120, blank=True)
    state = models.CharField(_("state / province"), max_length=120, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=32, blank=True)
    country = models.CharField(_("country"), max_length=2, default="US")

    # ---- Locale & finance ----
    timezone = models.CharField(_("timezone"), max_length=64, default="UTC")
    currency = models.CharField(
        _("currency"), max_length=3, choices=Currency.choices, default=Currency.USD
    )
    fiscal_year_start_month = models.PositiveSmallIntegerField(
        _("fiscal year start month"), default=1
    )
    tax_number = models.CharField(_("tax number"), max_length=64, blank=True)

    # ---- Subscription ----
    plan = models.CharField(_("plan"), max_length=20, choices=Plan.choices, default=Plan.FREE)
    trial_ends_at = models.DateTimeField(_("trial ends at"), null=True, blank=True)
    subscription_ends_at = models.DateTimeField(_("subscription ends at"), null=True, blank=True)
    max_users = models.PositiveIntegerField(_("seat limit"), default=5)
    max_storage_mb = models.PositiveIntegerField(_("storage limit (MB)"), default=1024)

    # ---- Status ----
    is_active = models.BooleanField(_("active"), default=True)
    onboarding_completed = models.BooleanField(_("onboarding completed"), default=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_organizations",
        verbose_name=_("owner"),
    )

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Derived state
    # ------------------------------------------------------------------
    @property
    def member_count(self) -> int:
        return self.memberships.filter(is_active=True).count()

    @property
    def seats_remaining(self) -> int:
        return max(self.max_users - self.member_count, 0)

    @property
    def is_on_trial(self) -> bool:
        return bool(self.trial_ends_at and timezone.now() < self.trial_ends_at)

    @property
    def is_subscription_active(self) -> bool:
        if self.plan == self.Plan.FREE:
            return True
        if self.is_on_trial:
            return True
        return bool(self.subscription_ends_at and timezone.now() < self.subscription_ends_at)

    def can_add_member(self) -> bool:
        return self.seats_remaining > 0

    @property
    def full_address(self) -> str:
        parts = [
            self.address_line1, self.address_line2, self.city,
            self.state, self.postal_code, self.country,
        ]
        return ", ".join(part for part in parts if part)


class OrganizationSettings(BaseModel):
    """Per-tenant feature switches and defaults."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name=_("organization"),
    )

    # ---- Feature switches ----
    ai_assistant_enabled = models.BooleanField(_("AI assistant enabled"), default=True)
    lead_scoring_enabled = models.BooleanField(_("AI lead scoring enabled"), default=True)
    email_notifications_enabled = models.BooleanField(_("email notifications"), default=True)
    realtime_notifications_enabled = models.BooleanField(_("realtime notifications"), default=True)
    audit_logging_enabled = models.BooleanField(_("audit logging"), default=True)
    allow_public_signup = models.BooleanField(_("allow public signup"), default=False)
    require_email_verification = models.BooleanField(_("require email verification"), default=True)
    two_factor_required = models.BooleanField(_("require two-factor"), default=False)

    # ---- Defaults ----
    default_deal_probability = models.PositiveSmallIntegerField(
        _("default deal probability"), default=20
    )
    default_task_reminder_minutes = models.PositiveIntegerField(
        _("default task reminder (minutes)"), default=30
    )
    ticket_sla_hours = models.PositiveIntegerField(_("ticket SLA (hours)"), default=24)
    working_days = models.JSONField(_("working days"), default=list, blank=True)
    working_hours_start = models.TimeField(_("working hours start"), null=True, blank=True)
    working_hours_end = models.TimeField(_("working hours end"), null=True, blank=True)

    # ---- Integrations ----
    email_signature = models.TextField(_("email signature"), blank=True, max_length=2000)
    webhook_url = models.URLField(_("webhook URL"), blank=True)
    custom_fields_schema = models.JSONField(_("custom fields schema"), default=dict, blank=True)

    class Meta:
        verbose_name = _("organization settings")
        verbose_name_plural = _("organization settings")

    def __str__(self) -> str:
        return f"Settings for {self.organization_id}"

    @staticmethod
    def default_working_days() -> list[int]:
        """Monday to Friday, ISO weekday numbers."""
        return [1, 2, 3, 4, 5]


class OrganizationMembership(BaseModel):
    """Links a user to an organization with a role."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("organization"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("user"),
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=OrganizationRole.choices,
        default=OrganizationRole.MEMBER,
    )
    title = models.CharField(_("title"), max_length=120, blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    joined_at = models.DateTimeField(_("joined at"), default=timezone.now)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_memberships",
        verbose_name=_("invited by"),
    )

    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name=_("department"),
    )

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                condition=models.Q(is_deleted=False),
                name="uniq_membership_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.organization_id} ({self.role})"

    @property
    def is_owner(self) -> bool:
        return self.role == OrganizationRole.OWNER

    @property
    def is_admin(self) -> bool:
        return self.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}


class Department(TenantBaseModel):
    """An organizational unit, e.g. Sales, Support, Engineering."""

    name = models.CharField(_("name"), max_length=120)
    code = models.CharField(_("code"), max_length=32, blank=True)
    description = models.TextField(_("description"), blank=True, max_length=1000)
    color = models.CharField(
        _("colour"), max_length=7, default="#64748b", validators=[hex_color_validator]
    )
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
        verbose_name=_("department head"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("parent department"),
    )

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                condition=models.Q(is_deleted=False),
                name="uniq_department_name_per_org",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def member_count(self) -> int:
        return self.members.filter(is_active=True).count()


class Team(TenantBaseModel):
    """A working group that owns records and receives assignments together."""

    name = models.CharField(_("name"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, blank=True)
    description = models.TextField(_("description"), blank=True, max_length=1000)
    color = models.CharField(
        _("colour"), max_length=7, default="#2563eb", validators=[hex_color_validator]
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teams",
        verbose_name=_("department"),
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_teams",
        verbose_name=_("team lead"),
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="organizations.TeamMembership",
        through_fields=("team", "user"),
        related_name="teams",
        verbose_name=_("members"),
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("team")
        verbose_name_plural = _("teams")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(is_deleted=False),
                name="uniq_team_slug_per_org",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    @property
    def member_count(self) -> int:
        return self.team_memberships.filter(is_active=True).count()


class TeamMembership(TenantBaseModel):
    """Membership of a :class:`Team`, with an in-team role."""

    class TeamRole(models.TextChoices):
        LEAD = "lead", _("Lead")
        MEMBER = "member", _("Member")

    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="team_memberships", verbose_name=_("team")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
        verbose_name=_("user"),
    )
    role = models.CharField(
        _("team role"), max_length=16, choices=TeamRole.choices, default=TeamRole.MEMBER
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("team membership")
        verbose_name_plural = _("team memberships")
        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                condition=models.Q(is_deleted=False),
                name="uniq_team_membership",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.team_id}"


class Invitation(TenantBaseModel):
    """A pending invitation for someone to join the organization."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        DECLINED = "declined", _("Declined")
        EXPIRED = "expired", _("Expired")
        REVOKED = "revoked", _("Revoked")

    email = models.EmailField(_("email"), db_index=True)
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=OrganizationRole.choices,
        default=OrganizationRole.MEMBER,
    )
    token = models.CharField(_("token"), max_length=128, unique=True, db_index=True)
    status = models.CharField(
        _("status"), max_length=16, choices=Status.choices, default=Status.PENDING
    )
    message = models.TextField(_("message"), blank=True, max_length=1000)
    expires_at = models.DateTimeField(_("expires at"))
    accepted_at = models.DateTimeField(_("accepted at"), null=True, blank=True)

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
        verbose_name=_("invited by"),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations",
        verbose_name=_("team"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations",
        verbose_name=_("department"),
    )

    class Meta(TenantBaseModel.Meta):
        verbose_name = _("invitation")
        verbose_name_plural = _("invitations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["email", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} -> {self.organization_id} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = generate_token(64)
        if not self.expires_at:
            days = getattr(settings, "INVITATION_TTL_DAYS", 14)
            self.expires_at = timezone.now() + timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING and not self.is_expired
