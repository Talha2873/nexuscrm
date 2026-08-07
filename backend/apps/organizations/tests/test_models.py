"""Unit tests for tenant models."""
import pytest
from django.utils import timezone

from apps.organizations.models import Invitation, Organization, OrganizationMembership

pytestmark = pytest.mark.django_db


class TestOrganization:
    def test_slug_is_generated_from_name(self):
        organization = Organization.objects.create(name="Wayne Enterprises")
        assert organization.slug == "wayne-enterprises"

    def test_slugs_are_unique(self):
        Organization.objects.create(name="Duplicate Co")
        second = Organization.objects.create(name="Duplicate Co")
        assert second.slug == "duplicate-co-2"

    def test_member_count_and_seats(self, organization, owner_user, member_user):
        assert organization.member_count == 2
        assert organization.seats_remaining == organization.max_users - 2
        assert organization.can_add_member() is True

    def test_seat_limit_blocks_new_members(self, organization, owner_user):
        organization.max_users = 1
        organization.save(update_fields=["max_users"])
        assert organization.can_add_member() is False

    def test_trial_state(self, organization):
        assert organization.is_on_trial is False
        organization.trial_ends_at = timezone.now() + timezone.timedelta(days=5)
        organization.save(update_fields=["trial_ends_at"])
        assert organization.is_on_trial is True

    def test_settings_row_is_created_automatically(self):
        organization = Organization.objects.create(name="Auto Settings Inc")
        assert organization.settings is not None
        assert organization.settings.ai_assistant_enabled is True


class TestMembership:
    def test_first_membership_becomes_active_organization(self, organization):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            email="fresh@example.com", password="Passw0rd!23", first_name="Fresh"
        )
        assert user.active_organization_id is None
        OrganizationMembership.objects.create(
            organization=organization, user=user, role="member"
        )
        user.refresh_from_db()
        assert user.active_organization_id == organization.id

    def test_role_helpers(self, owner_user, organization):
        membership = owner_user.membership_for(organization)
        assert membership.is_owner and membership.is_admin


class TestInvitation:
    def test_token_and_expiry_are_populated(self, organization, owner_user):
        invitation = Invitation.objects.create(
            organization=organization, email="invitee@example.com", invited_by=owner_user
        )
        assert invitation.token and len(invitation.token) == 64
        assert invitation.expires_at > timezone.now()
        assert invitation.is_pending is True

    def test_expired_invitation_is_not_pending(self, organization):
        invitation = Invitation.objects.create(
            organization=organization,
            email="late@example.com",
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        assert invitation.is_expired is True
        assert invitation.is_pending is False
