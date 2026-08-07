"""Unit tests for the authentication service layer."""
import pytest

from apps.accounts.models import PasswordResetToken
from apps.accounts.services import AuthService, ProfileService
from apps.common.exceptions import (
    BusinessRuleViolation,
    DuplicateResource,
    PermissionDeniedError,
    ServiceError,
)

pytestmark = pytest.mark.django_db


class TestAuthServiceRegistration:
    def test_register_creates_owner_membership(self):
        result = AuthService().register(
            email="founder@example.com",
            password="Str0ngPassw0rd!",
            first_name="Fiona",
            organization_name="Founder Co",
        )
        user, organization = result["user"], result["organization"]
        assert organization.name == "Founder Co"
        assert user.role_in(organization) == "owner"
        assert user.active_organization_id == organization.id

    def test_register_rejects_duplicate_email(self, member_user):
        with pytest.raises(DuplicateResource):
            AuthService().register(
                email=member_user.email,
                password="Str0ngPassw0rd!",
                first_name="Clash",
            )


class TestAuthServiceLogin:
    def test_login_increments_login_count(self, member_user, password):
        before = member_user.login_count
        AuthService().login(member_user.email, password)
        member_user.refresh_from_db()
        assert member_user.login_count == before + 1

    def test_login_with_bad_password_raises(self, member_user):
        with pytest.raises(ServiceError):
            AuthService().login(member_user.email, "wrong")

    def test_login_records_a_failed_attempt(self, member_user):
        from apps.accounts.models import LoginAttempt

        with pytest.raises(ServiceError):
            AuthService().login(member_user.email, "wrong")
        assert LoginAttempt.objects.filter(email=member_user.email, succeeded=False).exists()


class TestPasswordManagement:
    def test_reset_password_consumes_the_token(self, member_user):
        token = PasswordResetToken.issue(member_user)
        AuthService().reset_password(token.token, "An0therPass!")
        token.refresh_from_db()
        assert token.is_used
        member_user.refresh_from_db()
        assert member_user.check_password("An0therPass!")

    def test_reset_password_rejects_a_used_token(self, member_user):
        token = PasswordResetToken.issue(member_user)
        AuthService().reset_password(token.token, "An0therPass!")
        with pytest.raises(ServiceError):
            AuthService().reset_password(token.token, "YetAn0ther!")

    def test_change_password_rejects_reuse(self, member_user, password):
        with pytest.raises(BusinessRuleViolation):
            AuthService().change_password(member_user, password, password)


class TestOrganizationSwitching:
    def test_switch_to_a_membership_organization(self, member_user, organization):
        result = AuthService().switch_organization(member_user, organization.id)
        assert result.id == organization.id

    def test_switch_to_a_foreign_organization_is_denied(self, member_user, other_organization):
        with pytest.raises(PermissionDeniedError):
            AuthService().switch_organization(member_user, other_organization.id)


class TestProfileService:
    def test_update_profile_ignores_protected_fields(self, member_user):
        ProfileService().update_profile(
            member_user, first_name="Renamed", is_superuser=True
        )
        member_user.refresh_from_db()
        assert member_user.first_name == "Renamed"
        assert member_user.is_superuser is False

    def test_owner_cannot_deactivate_without_transferring(self, owner_user):
        with pytest.raises(BusinessRuleViolation):
            ProfileService().deactivate(owner_user)
