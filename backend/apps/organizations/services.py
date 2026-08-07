"""Tenant business logic: provisioning, membership, teams and invitations."""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.constants import ROLE_HIERARCHY, ActivityVerb, OrganizationRole
from apps.common.exceptions import (
    BusinessRuleViolation,
    DuplicateResource,
    PermissionDeniedError,
    ResourceNotFound,
    ServiceError,
)
from apps.common.services import ActivityService, BaseService
from apps.common.utils import normalise_email, unique_slugify

from .models import Department, Invitation, Organization, OrganizationMembership, Team
from .repositories import (
    DepartmentRepository,
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    OrganizationSettingsRepository,
    TeamMembershipRepository,
    TeamRepository,
)

logger = logging.getLogger(__name__)


class OrganizationService(BaseService):
    """Creating and maintaining tenants."""

    repository_class = OrganizationRepository
    entity_name = "Organization"

    def __init__(self, repository=None) -> None:
        super().__init__(repository)
        self.memberships = MembershipRepository()
        self.settings = OrganizationSettingsRepository()

    @transaction.atomic
    def create_for_owner(self, owner, name: str, **extra) -> Organization:
        """Provision a brand-new tenant and make ``owner`` its owner."""
        name = (name or "").strip() or f"{owner.get_short_name()}'s workspace"

        organization = Organization(name=name, owner=owner, **extra)
        organization.slug = unique_slugify(organization, name)
        organization.created_by = owner
        organization.save()

        OrganizationMembership.objects.create(
            organization=organization,
            user=owner,
            role=OrganizationRole.OWNER,
            is_active=True,
            created_by=owner,
        )

        self.settings.get_for_organization(organization)
        self._seed_defaults(organization, owner)

        ActivityService.record(
            organization,
            ActivityVerb.CREATED,
            f"Organization '{organization.name}' was created",
            actor=owner,
            organization=organization,
        )
        logger.info("Provisioned organization %s for %s", organization.slug, owner.email)
        return organization

    def _seed_defaults(self, organization: Organization, owner) -> None:
        """Give a new tenant a usable pipeline and department out of the box."""
        try:
            from apps.deals.services import PipelineService

            PipelineService().create_default_pipeline(organization=organization, actor=owner)
        except Exception:  # pragma: no cover - seeding must not block signup
            logger.exception("Could not seed default pipeline for %s", organization.slug)

        try:
            Department.objects.create(
                organization=organization, name="General", code="GEN", created_by=owner
            )
        except Exception:  # pragma: no cover
            logger.exception("Could not seed default department for %s", organization.slug)

    @transaction.atomic
    def update_organization(self, organization: Organization, actor, **payload) -> Organization:
        membership = actor.membership_for(organization) if not actor.is_superuser else None
        if not actor.is_superuser and (
            membership is None
            or ROLE_HIERARCHY.get(membership.role, 0) < ROLE_HIERARCHY[OrganizationRole.ADMIN]
        ):
            raise PermissionDeniedError("Only administrators can edit organization details.")

        if "slug" in payload and payload["slug"] != organization.slug:
            if self.repository.slug_taken(payload["slug"], exclude_id=organization.id):
                raise DuplicateResource("That workspace URL is already taken.")

        for field, value in payload.items():
            setattr(organization, field, value)
        organization.updated_by = actor
        organization.save()

        ActivityService.record(
            organization,
            ActivityVerb.UPDATED,
            f"Organization '{organization.name}' was updated",
            actor=actor,
            organization=organization,
            metadata={"fields": sorted(payload.keys())},
        )
        return organization

    @transaction.atomic
    def transfer_ownership(self, organization: Organization, actor, new_owner_id) -> Organization:
        if not actor.is_superuser and organization.owner_id != actor.id:
            raise PermissionDeniedError("Only the current owner can transfer ownership.")

        new_membership = OrganizationMembership.objects.filter(
            organization=organization, user_id=new_owner_id, is_active=True
        ).first()
        if new_membership is None:
            raise ResourceNotFound("That user is not an active member of this organization.")

        old_membership = OrganizationMembership.objects.filter(
            organization=organization, user=organization.owner
        ).first()
        if old_membership is not None:
            old_membership.role = OrganizationRole.ADMIN
            old_membership.save(update_fields=["role", "updated_at"])

        new_membership.role = OrganizationRole.OWNER
        new_membership.save(update_fields=["role", "updated_at"])

        organization.owner_id = new_owner_id
        organization.save(update_fields=["owner", "updated_at"])

        ActivityService.record(
            organization,
            ActivityVerb.UPDATED,
            "Organization ownership was transferred",
            actor=actor,
            organization=organization,
        )
        return organization

    def get_settings(self, organization):
        return self.settings.get_for_organization(organization)

    @transaction.atomic
    def update_settings(self, organization, actor, **payload):
        settings_obj = self.settings.get_for_organization(organization)
        for field, value in payload.items():
            setattr(settings_obj, field, value)
        settings_obj.updated_by = actor
        settings_obj.save()
        return settings_obj

    def statistics(self, organization) -> dict:
        """Headline numbers for the organization settings screen."""
        from django.db.models import Count, Sum

        from apps.common.models import Document

        storage = (
            Document.objects.filter(organization=organization).aggregate(
                total=Sum("file_size")
            )["total"]
            or 0
        )
        counts = OrganizationMembership.objects.filter(
            organization=organization, is_active=True
        ).aggregate(members=Count("id"))

        return {
            "member_count": counts["members"],
            "seats_total": organization.max_users,
            "seats_remaining": organization.seats_remaining,
            "team_count": Team.objects.filter(organization=organization).count(),
            "department_count": Department.objects.filter(organization=organization).count(),
            "storage_used_bytes": storage,
            "storage_limit_bytes": organization.max_storage_mb * 1024 * 1024,
            "plan": organization.plan,
            "is_on_trial": organization.is_on_trial,
            "trial_ends_at": organization.trial_ends_at,
        }


class MembershipService(BaseService):
    """Managing who belongs to the organization and with what role."""

    repository_class = MembershipRepository
    entity_name = "Membership"

    @transaction.atomic
    def change_role(self, membership: OrganizationMembership, actor, new_role: str):
        actor_membership = actor.membership_for(membership.organization)
        actor_rank = (
            999 if actor.is_superuser else ROLE_HIERARCHY.get(getattr(actor_membership, "role", ""), 0)
        )

        if actor_rank < ROLE_HIERARCHY[OrganizationRole.ADMIN]:
            raise PermissionDeniedError("Only administrators can change roles.")
        if new_role == OrganizationRole.OWNER:
            raise BusinessRuleViolation(
                "Use the ownership transfer endpoint to assign a new owner."
            )
        if membership.role == OrganizationRole.OWNER:
            raise BusinessRuleViolation("The owner's role cannot be changed directly.")
        if ROLE_HIERARCHY.get(new_role, 0) > actor_rank:
            raise PermissionDeniedError("You cannot grant a role above your own.")

        membership.role = new_role
        membership.updated_by = actor
        membership.save(update_fields=["role", "updated_by", "updated_at"])

        ActivityService.record(
            membership.organization,
            ActivityVerb.UPDATED,
            f"{membership.user} is now a {membership.get_role_display()}",
            actor=actor,
            organization=membership.organization,
        )
        return membership

    @transaction.atomic
    def deactivate(self, membership: OrganizationMembership, actor):
        if membership.role == OrganizationRole.OWNER:
            raise BusinessRuleViolation("The organization owner cannot be removed.")
        if membership.user_id == actor.id:
            raise BusinessRuleViolation("Use the leave endpoint to remove yourself.")

        actor_membership = actor.membership_for(membership.organization)
        if not actor.is_superuser and (
            actor_membership is None
            or ROLE_HIERARCHY.get(actor_membership.role, 0) < ROLE_HIERARCHY[OrganizationRole.ADMIN]
        ):
            raise PermissionDeniedError("Only administrators can remove members.")

        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])

        user = membership.user
        if user.active_organization_id == membership.organization_id:
            user.active_organization = user.organizations().exclude(
                id=membership.organization_id
            ).first()
            user.save(update_fields=["active_organization", "updated_at"])

        ActivityService.record(
            membership.organization,
            ActivityVerb.UPDATED,
            f"{membership.user} was removed from the organization",
            actor=actor,
            organization=membership.organization,
        )
        return membership

    @transaction.atomic
    def leave(self, organization, user):
        membership = OrganizationMembership.objects.filter(
            organization=organization, user=user, is_active=True
        ).first()
        if membership is None:
            raise ResourceNotFound("You are not a member of this organization.")
        if membership.role == OrganizationRole.OWNER:
            raise BusinessRuleViolation(
                "Transfer ownership before leaving the organization."
            )

        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])

        if user.active_organization_id == organization.id:
            user.active_organization = user.organizations().exclude(id=organization.id).first()
            user.save(update_fields=["active_organization", "updated_at"])
        return membership

    @transaction.atomic
    def reactivate(self, membership: OrganizationMembership, actor):
        if not membership.organization.can_add_member():
            raise BusinessRuleViolation(
                "This organization has no seats left. Upgrade the plan first."
            )
        membership.is_active = True
        membership.updated_by = actor
        membership.save(update_fields=["is_active", "updated_by", "updated_at"])
        return membership


class TeamService(BaseService):
    """Team creation and membership."""

    repository_class = TeamRepository
    entity_name = "Team"

    def __init__(self, repository=None) -> None:
        super().__init__(repository)
        self.team_memberships = TeamMembershipRepository()

    @transaction.atomic
    def add_member(self, team: Team, user_id, role: str = "member"):
        if not OrganizationMembership.objects.filter(
            organization=team.organization, user_id=user_id, is_active=True
        ).exists():
            raise BusinessRuleViolation(
                "Only members of the organization can join a team."
            )

        from .models import TeamMembership

        membership, created = TeamMembership.objects.get_or_create(
            team=team,
            user_id=user_id,
            defaults={"organization": team.organization, "role": role, "is_active": True},
        )
        if not created:
            membership.is_active = True
            membership.role = role
            membership.save(update_fields=["is_active", "role", "updated_at"])

        ActivityService.record(
            team,
            ActivityVerb.ASSIGNED,
            f"A member was added to team '{team.name}'",
            organization=team.organization,
        )
        return membership

    @transaction.atomic
    def remove_member(self, team: Team, user_id):
        membership = self.team_memberships.get_queryset().filter(
            team=team, user_id=user_id
        ).first()
        if membership is None:
            raise ResourceNotFound("That user is not in this team.")
        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        return membership


class DepartmentService(BaseService):
    repository_class = DepartmentRepository
    entity_name = "Department"

    def before_delete(self, instance) -> None:
        if instance.children.exists():
            raise BusinessRuleViolation(
                "Reassign or remove child departments before deleting this one."
            )


class InvitationService(BaseService):
    """Inviting people into the organization."""

    repository_class = InvitationRepository
    entity_name = "Invitation"

    @transaction.atomic
    def invite(
        self,
        organization,
        inviter,
        email: str,
        role: str = OrganizationRole.MEMBER,
        message: str = "",
        team=None,
        department=None,
    ) -> Invitation:
        email = normalise_email(email)

        inviter_membership = inviter.membership_for(organization)
        inviter_rank = (
            999 if inviter.is_superuser else ROLE_HIERARCHY.get(getattr(inviter_membership, "role", ""), 0)
        )
        if inviter_rank < ROLE_HIERARCHY[OrganizationRole.MANAGER]:
            raise PermissionDeniedError("You do not have permission to invite members.")
        if ROLE_HIERARCHY.get(role, 0) > inviter_rank:
            raise PermissionDeniedError("You cannot invite someone at a higher role than your own.")
        if role == OrganizationRole.OWNER:
            raise BusinessRuleViolation("An organization can only have one owner.")

        if not organization.can_add_member():
            raise BusinessRuleViolation(
                "No seats remaining. Upgrade your plan to invite more people."
            )

        if OrganizationMembership.objects.filter(
            organization=organization, user__email__iexact=email, is_active=True
        ).exists():
            raise DuplicateResource("That person is already a member of this organization.")

        existing = self.repository.pending_for_email(organization, email)
        if existing is not None:
            raise DuplicateResource("An invitation is already pending for that address.")

        invitation = Invitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            message=message,
            invited_by=inviter,
            team=team,
            department=department,
            created_by=inviter,
        )

        from .tasks import send_invitation_email

        send_invitation_email.delay(str(invitation.id))

        ActivityService.record(
            invitation,
            ActivityVerb.CREATED,
            f"{email} was invited as {invitation.get_role_display()}",
            actor=inviter,
            organization=organization,
        )
        return invitation

    @transaction.atomic
    def accept(self, token: str, user) -> Organization:
        invitation = self.repository.get_by_token(token)
        if invitation is None:
            raise ResourceNotFound("This invitation link is not valid.")
        if invitation.status != Invitation.Status.PENDING:
            raise BusinessRuleViolation(
                f"This invitation has already been {invitation.get_status_display().lower()}."
            )
        if invitation.is_expired:
            invitation.status = Invitation.Status.EXPIRED
            invitation.save(update_fields=["status", "updated_at"])
            raise BusinessRuleViolation("This invitation has expired.")
        if normalise_email(user.email) != normalise_email(invitation.email):
            raise PermissionDeniedError(
                "This invitation was sent to a different email address."
            )

        organization = invitation.organization
        if not organization.can_add_member():
            raise BusinessRuleViolation("This organization has no seats remaining.")

        membership, _created = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={
                "role": invitation.role,
                "invited_by": invitation.invited_by,
                "department": invitation.department,
                "is_active": True,
            },
        )
        if not membership.is_active:
            membership.is_active = True
            membership.role = invitation.role
            membership.save(update_fields=["is_active", "role", "updated_at"])

        if invitation.team_id:
            TeamService().add_member(invitation.team, user.id)

        invitation.status = Invitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at", "updated_at"])

        ActivityService.record(
            organization,
            ActivityVerb.CREATED,
            f"{user} joined the organization",
            actor=user,
            organization=organization,
        )

        from apps.accounts.tasks import send_welcome_email

        send_welcome_email.delay(str(user.id), organization.name)
        return organization

    @transaction.atomic
    def revoke(self, invitation: Invitation, actor) -> Invitation:
        if invitation.status != Invitation.Status.PENDING:
            raise BusinessRuleViolation("Only pending invitations can be revoked.")
        invitation.status = Invitation.Status.REVOKED
        invitation.updated_by = actor
        invitation.save(update_fields=["status", "updated_by", "updated_at"])
        return invitation

    @transaction.atomic
    def resend(self, invitation: Invitation, actor) -> Invitation:
        if invitation.status != Invitation.Status.PENDING:
            raise BusinessRuleViolation("Only pending invitations can be resent.")

        from datetime import timedelta

        invitation.expires_at = timezone.now() + timedelta(
            days=getattr(settings, "INVITATION_TTL_DAYS", 14)
        )
        invitation.updated_by = actor
        invitation.save(update_fields=["expires_at", "updated_by", "updated_at"])

        from .tasks import send_invitation_email

        send_invitation_email.delay(str(invitation.id))
        return invitation

    def preview(self, token: str) -> dict:
        """Public, unauthenticated view of an invitation (shown before signup)."""
        invitation = self.repository.get_by_token(token)
        if invitation is None:
            raise ResourceNotFound("This invitation link is not valid.")
        return {
            "email": invitation.email,
            "role": invitation.role,
            "role_display": invitation.get_role_display(),
            "organization_name": invitation.organization.name,
            "invited_by": str(invitation.invited_by) if invitation.invited_by else "",
            "message": invitation.message,
            "expires_at": invitation.expires_at,
            "is_valid": invitation.is_pending,
            "status": invitation.status,
        }
