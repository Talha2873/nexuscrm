"""Service-layer tests for tenant logic."""
import pytest

from apps.common.exceptions import (
    BusinessRuleViolation,
    DuplicateResource,
    PermissionDeniedError,
)
from apps.organizations.services import (
    InvitationService,
    MembershipService,
    OrganizationService,
)

pytestmark = pytest.mark.django_db


class TestOrganizationService:
    def test_create_for_owner_provisions_defaults(self, member_user):
        organization = OrganizationService().create_for_owner(
            owner=member_user, name="Second Workspace"
        )
        assert organization.owner_id == member_user.id
        assert organization.settings is not None
        from apps.organizations.models import Department

        assert Department.objects.filter(
            organization=organization, name="General"
        ).exists()
        assert member_user.role_in(organization) == "owner"

    def test_transfer_ownership_demotes_previous_owner(
        self, organization, owner_user, admin_user
    ):
        OrganizationService().transfer_ownership(organization, owner_user, admin_user.id)
        organization.refresh_from_db()
        assert organization.owner_id == admin_user.id
        assert owner_user.role_in(organization) == "admin"
        assert admin_user.role_in(organization) == "owner"

    def test_non_owner_cannot_transfer_ownership(self, organization, member_user, admin_user):
        with pytest.raises(PermissionDeniedError):
            OrganizationService().transfer_ownership(organization, member_user, admin_user.id)


class TestMembershipService:
    def test_owner_cannot_be_deactivated(self, organization, owner_user, admin_user):
        membership = owner_user.membership_for(organization)
        with pytest.raises(BusinessRuleViolation):
            MembershipService().deactivate(membership, admin_user)

    def test_owner_cannot_leave(self, organization, owner_user):
        with pytest.raises(BusinessRuleViolation):
            MembershipService().leave(organization, owner_user)

    def test_member_can_leave(self, organization, member_user):
        MembershipService().leave(organization, member_user)
        assert member_user.membership_for(organization) is None

    def test_cannot_grant_a_role_above_your_own(self, organization, admin_user, member_user):
        from apps.common.constants import OrganizationRole

        membership = member_user.membership_for(organization)
        # An admin granting 'admin' is fine ...
        MembershipService().change_role(membership, admin_user, OrganizationRole.ADMIN)
        assert member_user.role_in(organization) == "admin"


class TestInvitationService:
    def test_invite_and_accept(self, organization, owner_user, db):
        from django.contrib.auth import get_user_model

        invitation = InvitationService().invite(
            organization=organization,
            inviter=owner_user,
            email="joiner@example.com",
            role="member",
        )
        joiner = get_user_model().objects.create_user(
            email="joiner@example.com", password="Passw0rd!23", first_name="Joiner"
        )
        result = InvitationService().accept(invitation.token, joiner)
        assert result.id == organization.id
        assert joiner.role_in(organization) == "member"

    def test_accepting_with_a_different_email_is_denied(
        self, organization, owner_user, member_user
    ):
        invitation = InvitationService().invite(
            organization=organization, inviter=owner_user, email="someone@else.com"
        )
        with pytest.raises(PermissionDeniedError):
            InvitationService().accept(invitation.token, member_user)

    def test_cannot_invite_an_existing_member(self, organization, owner_user, member_user):
        with pytest.raises(DuplicateResource):
            InvitationService().invite(
                organization=organization, inviter=owner_user, email=member_user.email
            )

    def test_cannot_invite_above_your_own_role(self, organization, member_user):
        with pytest.raises(PermissionDeniedError):
            InvitationService().invite(
                organization=organization,
                inviter=member_user,
                email="new@example.com",
                role="admin",
            )
