"""API tests for organization management, including tenant isolation."""
import pytest
from django.urls import reverse

from apps.organizations.models import Department, Team

pytestmark = [pytest.mark.django_db, pytest.mark.api]


class TestOrganizationEndpoints:
    def test_list_returns_only_my_organizations(self, auth_client, organization, other_organization):
        response = auth_client.get(reverse("v1:organizations:organization-list"))
        assert response.status_code == 200
        names = {row["name"] for row in response.data["results"]}
        assert names == {organization.name}

    def test_current_returns_active_organization(self, auth_client, organization):
        response = auth_client.get(reverse("v1:organizations:organization-current"))
        assert response.status_code == 200
        assert response.data["id"] == str(organization.id)

    def test_member_cannot_update_organization(self, auth_client, organization):
        response = auth_client.patch(
            reverse("v1:organizations:organization-detail", args=[organization.id]),
            {"name": "Renamed by member"},
            format="json",
        )
        assert response.status_code == 403

    def test_admin_can_update_organization(self, admin_client, organization):
        response = admin_client.patch(
            reverse("v1:organizations:organization-detail", args=[organization.id]),
            {"name": "Acme Global", "city": "Lahore"},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["name"] == "Acme Global"

    def test_foreign_user_cannot_read_organization(self, foreign_client, organization):
        response = foreign_client.get(
            reverse("v1:organizations:organization-detail", args=[organization.id])
        )
        assert response.status_code == 404

    def test_stats_endpoint(self, admin_client, organization):
        response = admin_client.get(
            reverse("v1:organizations:organization-stats", args=[organization.id])
        )
        assert response.status_code == 200
        assert response.data["member_count"] >= 1
        assert "storage_used_bytes" in response.data


class TestMembershipEndpoints:
    def test_members_are_listed(self, auth_client, owner_user, member_user):
        response = auth_client.get(reverse("v1:organizations:membership-list"))
        assert response.status_code == 200
        emails = {row["user"]["email"] for row in response.data["results"]}
        assert member_user.email in emails

    def test_me_returns_own_membership(self, auth_client, member_user):
        response = auth_client.get(reverse("v1:organizations:membership-me"))
        assert response.status_code == 200
        assert response.data["role"] == "member"

    def test_member_cannot_change_roles(self, auth_client, owner_user, organization):
        membership = owner_user.membership_for(organization)
        response = auth_client.post(
            reverse("v1:organizations:membership-change-role", args=[membership.id]),
            {"role": "viewer"},
            format="json",
        )
        assert response.status_code == 403

    def test_admin_can_change_a_members_role(self, admin_client, member_user, organization):
        membership = member_user.membership_for(organization)
        response = admin_client.post(
            reverse("v1:organizations:membership-change-role", args=[membership.id]),
            {"role": "manager"},
            format="json",
        )
        assert response.status_code == 200, response.data
        membership.refresh_from_db()
        assert membership.role == "manager"

    def test_owner_role_cannot_be_changed(self, admin_client, owner_user, organization):
        membership = owner_user.membership_for(organization)
        response = admin_client.post(
            reverse("v1:organizations:membership-change-role", args=[membership.id]),
            {"role": "viewer"},
            format="json",
        )
        assert response.status_code == 422


class TestTeamsAndDepartments:
    def test_manager_can_create_a_team(self, admin_client, organization):
        response = admin_client.post(
            reverse("v1:organizations:team-list"),
            {"name": "Enterprise Sales", "description": "Large accounts"},
            format="json",
        )
        assert response.status_code == 201, response.data
        assert Team.objects.filter(organization=organization, name="Enterprise Sales").exists()

    def test_viewer_role_cannot_create_a_department(self, auth_client):
        response = auth_client.post(
            reverse("v1:organizations:department-list"), {"name": "Ops"}, format="json"
        )
        assert response.status_code == 403

    def test_teams_are_isolated_between_organizations(
        self, admin_client, foreign_client, organization
    ):
        admin_client.post(
            reverse("v1:organizations:team-list"), {"name": "Secret Team"}, format="json"
        )
        response = foreign_client.get(reverse("v1:organizations:team-list"))
        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_add_and_remove_team_member(self, admin_client, organization, member_user):
        team = Team.objects.create(organization=organization, name="Pod A")
        add = admin_client.post(
            reverse("v1:organizations:team-add-member", args=[team.id]),
            {"user_id": str(member_user.id)},
            format="json",
        )
        assert add.status_code == 201, add.data
        assert team.team_memberships.filter(user=member_user, is_active=True).exists()

        remove = admin_client.post(
            reverse("v1:organizations:team-remove-member", args=[team.id]),
            {"user_id": str(member_user.id)},
            format="json",
        )
        assert remove.status_code == 200
        assert not team.team_memberships.filter(user=member_user, is_active=True).exists()

    def test_department_creation_and_listing(self, admin_client, organization):
        admin_client.post(
            reverse("v1:organizations:department-list"),
            {"name": "Customer Success", "code": "CS"},
            format="json",
        )
        assert Department.objects.filter(
            organization=organization, name="Customer Success"
        ).exists()


class TestInvitations:
    def test_admin_can_invite(self, admin_client, organization):
        response = admin_client.post(
            reverse("v1:organizations:invitation-list"),
            {"email": "recruit@example.com", "role": "member"},
            format="json",
        )
        assert response.status_code == 201, response.data
        assert response.data["status"] == "pending"

    def test_duplicate_invitation_is_rejected(self, admin_client):
        url = reverse("v1:organizations:invitation-list")
        admin_client.post(url, {"email": "twice@example.com"}, format="json")
        response = admin_client.post(url, {"email": "twice@example.com"}, format="json")
        assert response.status_code == 409

    def test_plain_member_cannot_invite(self, auth_client):
        response = auth_client.post(
            reverse("v1:organizations:invitation-list"),
            {"email": "nope@example.com"},
            format="json",
        )
        assert response.status_code == 403

    def test_invitation_preview_is_public(self, api_client, admin_client):
        created = admin_client.post(
            reverse("v1:organizations:invitation-list"),
            {"email": "preview@example.com"},
            format="json",
        )
        from apps.organizations.models import Invitation

        invitation = Invitation.objects.get(id=created.data["id"])
        response = api_client.get(
            reverse("v1:organizations:invitation-preview", args=[invitation.token])
        )
        assert response.status_code == 200
        assert response.data["organization_name"] == "Acme Corporation"
        assert response.data["is_valid"] is True
