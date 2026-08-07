"""End-to-end tests for the authentication API."""
import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import EmailVerificationToken, PasswordResetToken

pytestmark = [pytest.mark.django_db, pytest.mark.api]


class TestRegistration:
    def test_register_creates_user_organization_and_tokens(self, api_client):
        response = api_client.post(
            reverse("v1:accounts:register"),
            {
                "email": "new.user@example.com",
                "password": "Str0ngPassw0rd!",
                "password_confirm": "Str0ngPassw0rd!",
                "first_name": "New",
                "last_name": "User",
                "organization_name": "New Ventures",
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        body = response.data
        assert body["success"] is True
        assert body["user"]["email"] == "new.user@example.com"
        assert body["organization"]["name"] == "New Ventures"
        assert body["tokens"]["access"] and body["tokens"]["refresh"]

    def test_register_rejects_mismatched_passwords(self, api_client):
        response = api_client.post(
            reverse("v1:accounts:register"),
            {
                "email": "mismatch@example.com",
                "password": "Str0ngPassw0rd!",
                "password_confirm": "Different1!",
                "first_name": "Mis",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_register_rejects_weak_password(self, api_client):
        response = api_client.post(
            reverse("v1:accounts:register"),
            {
                "email": "weak@example.com",
                "password": "password",
                "password_confirm": "password",
                "first_name": "Weak",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_register_rejects_duplicate_email(self, api_client, member_user):
        response = api_client.post(
            reverse("v1:accounts:register"),
            {
                "email": member_user.email,
                "password": "Str0ngPassw0rd!",
                "password_confirm": "Str0ngPassw0rd!",
                "first_name": "Dup",
            },
            format="json",
        )
        assert response.status_code == 400


class TestLogin:
    def test_login_returns_tokens_and_user(self, api_client, member_user, password):
        response = api_client.post(
            reverse("v1:accounts:login"),
            {"email": member_user.email, "password": password},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["tokens"]["access"]
        assert response.data["user"]["email"] == member_user.email
        assert response.data["organization"]["name"] == "Acme Corporation"

    def test_login_with_wrong_password_fails(self, api_client, member_user):
        response = api_client.post(
            reverse("v1:accounts:login"),
            {"email": member_user.email, "password": "totally-wrong"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_credentials"

    def test_login_is_case_insensitive_on_email(self, api_client, member_user, password):
        response = api_client.post(
            reverse("v1:accounts:login"),
            {"email": member_user.email.upper(), "password": password},
            format="json",
        )
        assert response.status_code == 200

    def test_lockout_after_repeated_failures(self, api_client, member_user):
        url = reverse("v1:accounts:login")
        for _ in range(8):
            api_client.post(url, {"email": member_user.email, "password": "nope"}, format="json")
        response = api_client.post(
            url, {"email": member_user.email, "password": "nope"}, format="json"
        )
        assert response.status_code == 429


class TestTokens:
    def test_refresh_returns_a_new_access_token(self, api_client, member_user, password):
        login = api_client.post(
            reverse("v1:accounts:login"),
            {"email": member_user.email, "password": password},
            format="json",
        )
        refresh = login.data["tokens"]["refresh"]
        response = api_client.post(
            reverse("v1:accounts:token-refresh"), {"refresh": refresh}, format="json"
        )
        assert response.status_code == 200
        assert response.data["access"]

    def test_refresh_rejects_garbage(self, api_client):
        response = api_client.post(
            reverse("v1:accounts:token-refresh"), {"refresh": "not-a-token"}, format="json"
        )
        assert response.status_code == 401


class TestProfile:
    def test_me_requires_authentication(self, api_client):
        assert api_client.get(reverse("v1:accounts:me")).status_code == 401

    def test_me_returns_the_signed_in_user(self, auth_client, member_user):
        response = auth_client.get(reverse("v1:accounts:me"))
        assert response.status_code == 200
        assert response.data["user"]["email"] == member_user.email
        assert response.data["user"]["role"] == "member"

    def test_patch_me_updates_profile(self, auth_client):
        response = auth_client.patch(
            reverse("v1:accounts:me"),
            {"first_name": "Updated", "job_title": "Head of Revenue"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["user"]["first_name"] == "Updated"
        assert response.data["user"]["job_title"] == "Head of Revenue"

    def test_patch_me_rejects_blank_first_name(self, auth_client):
        response = auth_client.patch(
            reverse("v1:accounts:me"), {"first_name": "  "}, format="json"
        )
        assert response.status_code == 400


class TestEmailVerification:
    def test_verify_email_marks_user_verified(self, api_client, member_user):
        member_user.is_email_verified = False
        member_user.save(update_fields=["is_email_verified"])
        token = EmailVerificationToken.issue(member_user)

        response = api_client.post(
            reverse("v1:accounts:verify-email"), {"token": token.token}, format="json"
        )
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.is_email_verified is True

    def test_verify_email_rejects_unknown_token(self, api_client):
        response = api_client.post(
            reverse("v1:accounts:verify-email"), {"token": "nope"}, format="json"
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_verification_token"


class TestPasswordFlows:
    def test_forgot_password_never_reveals_account_existence(self, api_client):
        response = api_client.post(
            reverse("v1:accounts:forgot-password"),
            {"email": "nobody@example.com"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_reset_password_with_valid_token(self, api_client, member_user):
        token = PasswordResetToken.issue(member_user)
        response = api_client.post(
            reverse("v1:accounts:reset-password"),
            {
                "token": token.token,
                "password": "BrandNewP4ss!",
                "password_confirm": "BrandNewP4ss!",
            },
            format="json",
        )
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.check_password("BrandNewP4ss!")

    def test_change_password_requires_correct_current_password(self, auth_client):
        response = auth_client.post(
            reverse("v1:accounts:change-password"),
            {
                "current_password": "wrong-one",
                "new_password": "BrandNewP4ss!",
                "new_password_confirm": "BrandNewP4ss!",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_change_password_succeeds(self, auth_client, member_user, password):
        response = auth_client.post(
            reverse("v1:accounts:change-password"),
            {
                "current_password": password,
                "new_password": "BrandNewP4ss!",
                "new_password_confirm": "BrandNewP4ss!",
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        member_user.refresh_from_db()
        assert member_user.check_password("BrandNewP4ss!")


class TestSessions:
    def test_sessions_are_listed_for_the_user(self, api_client, member_user, password):
        login = api_client.post(
            reverse("v1:accounts:login"),
            {"email": member_user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['tokens']['access']}")
        response = api_client.get(reverse("v1:accounts:session-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_logout_blacklists_the_refresh_token(self, api_client, member_user, password):
        login = api_client.post(
            reverse("v1:accounts:login"),
            {"email": member_user.email, "password": password},
            format="json",
        )
        tokens = login.data["tokens"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        assert (
            api_client.post(
                reverse("v1:accounts:logout"), {"refresh": tokens["refresh"]}, format="json"
            ).status_code
            == 200
        )
        refreshed = api_client.post(
            reverse("v1:accounts:token-refresh"), {"refresh": tokens["refresh"]}, format="json"
        )
        assert refreshed.status_code == 401


class TestOrganizationSwitching:
    def test_user_cannot_switch_to_a_foreign_organization(
        self, auth_client, other_organization
    ):
        response = auth_client.post(
            reverse("v1:accounts:switch-organization"),
            {"organization_id": str(other_organization.id)},
            format="json",
        )
        assert response.status_code == 403
