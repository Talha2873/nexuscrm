"""Persistence gateways for tenant models."""
from __future__ import annotations

from django.utils import timezone

from apps.common.repositories import BaseRepository

from .models import (
    Department,
    Invitation,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    Team,
    TeamMembership,
)


class OrganizationRepository(BaseRepository):
    """Organizations are the tenant root, so reads are not tenant-filtered."""

    model = Organization
    select_related = ("owner",)
    default_ordering = ("name",)

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def get_by_slug(self, slug: str):
        return self.get_queryset().filter(slug=slug).first()

    def for_user(self, user):
        return self.get_queryset().filter(
            memberships__user=user, memberships__is_active=True
        ).distinct()

    def slug_taken(self, slug: str, exclude_id=None) -> bool:
        queryset = Organization.all_objects.filter(slug=slug)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()


class OrganizationSettingsRepository(BaseRepository):
    model = OrganizationSettings
    select_related = ("organization",)

    def get_queryset(self, include_deleted: bool = False):
        return self.get_base_queryset(include_deleted=include_deleted)

    def get_for_organization(self, organization):
        settings_obj, _created = OrganizationSettings.objects.get_or_create(
            organization=organization,
            defaults={"working_days": OrganizationSettings.default_working_days()},
        )
        return settings_obj


class MembershipRepository(BaseRepository):
    model = OrganizationMembership
    select_related = ("user", "organization", "department")
    default_ordering = ("-created_at",)

    def get_queryset(self, include_deleted: bool = False):
        """Memberships carry ``organization`` directly, so scope on it."""
        from apps.common.context import get_current_organization

        queryset = self.get_base_queryset(include_deleted=include_deleted)
        organization = get_current_organization()
        if organization is None:
            return queryset.none()
        return queryset.filter(organization_id=organization.id)

    def get_for(self, organization, user):
        return OrganizationMembership.objects.filter(
            organization=organization, user=user
        ).first()

    def active_members(self, organization):
        return OrganizationMembership.objects.filter(
            organization=organization, is_active=True
        ).select_related("user", "department")

    def owners(self, organization):
        return OrganizationMembership.objects.filter(
            organization=organization, role="owner", is_active=True
        )

    def count_active(self, organization) -> int:
        return OrganizationMembership.objects.filter(
            organization=organization, is_active=True
        ).count()


class DepartmentRepository(BaseRepository):
    model = Department
    select_related = ("head", "parent")
    default_ordering = ("name",)


class TeamRepository(BaseRepository):
    model = Team
    select_related = ("lead", "department")
    prefetch_related = ("team_memberships__user",)
    default_ordering = ("name",)

    def for_user(self, user):
        return self.get_queryset().filter(
            team_memberships__user=user, team_memberships__is_active=True
        ).distinct()


class TeamMembershipRepository(BaseRepository):
    model = TeamMembership
    select_related = ("team", "user")

    def get_for(self, team, user):
        return self.get_queryset().filter(team=team, user=user).first()


class InvitationRepository(BaseRepository):
    model = Invitation
    select_related = ("invited_by", "organization", "team", "department")
    default_ordering = ("-created_at",)

    def get_by_token(self, token: str):
        """Token lookups bypass tenant scoping: the invitee has no tenant yet."""
        return Invitation.objects.filter(token=token).select_related("organization").first()

    def pending_for_email(self, organization, email: str):
        return Invitation.objects.filter(
            organization=organization,
            email__iexact=email,
            status=Invitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        ).first()

    def expire_stale(self) -> int:
        return Invitation.objects.filter(
            status=Invitation.Status.PENDING, expires_at__lte=timezone.now()
        ).update(status=Invitation.Status.EXPIRED)
