"""Unit tests for the accounts models."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import (
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    UserSession,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestUserModel:
    def test_create_user_normalises_email(self):
        user = User.objects.create_user(
            email="  Casey@EXAMPLE.COM ", password="Passw0rd!23", first_name="Casey"
        )
        assert user.email == "Casey@example.com"
        assert user.check_password("Passw0rd!23")
        assert user.is_active is True
        assert user.is_email_verified is False

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError, match="email address"):
            User.objects.create_user(email="", password="Passw0rd!23", first_name="X")

    def test_create_superuser_is_verified_and_staff(self):
        admin = User.objects.create_superuser(
            email="root@example.com", password="Passw0rd!23", first_name="Root"
        )
        assert admin.is_staff and admin.is_superuser and admin.is_email_verified

    def test_full_name_and_initials(self):
        user = User(first_name="Ada", last_name="Lovelace", email="ada@example.com")
        assert user.full_name == "Ada Lovelace"
        assert user.initials == "AL"
        assert user.get_short_name() == "Ada"

    def test_soft_delete_hides_user_from_default_manager(self, member_user):
        member_user.delete()
        assert not User.objects.filter(pk=member_user.pk).exists()
        assert User.all_objects.filter(pk=member_user.pk).exists()

    def test_role_in_organization(self, member_user, organization):
        assert member_user.role_in(organization) == "member"

    def test_has_capability_true_for_admin(self, admin_user, organization):
        assert admin_user.has_capability("deals.delete", organization=organization) is True

    def test_has_capability_false_for_member_without_role(self, member_user, organization):
        assert member_user.has_capability("deals.delete", organization=organization) is False


class TestTokens:
    def test_verification_token_is_valid_then_consumed(self, member_user):
        token = EmailVerificationToken.issue(member_user)
        assert token.is_valid
        token.consume()
        assert token.is_used and not token.is_valid

    def test_issuing_a_new_token_invalidates_the_previous_one(self, member_user):
        first = EmailVerificationToken.issue(member_user)
        EmailVerificationToken.issue(member_user)
        first.refresh_from_db()
        assert first.is_used

    def test_expired_reset_token_is_invalid(self, member_user):
        token = PasswordResetToken.issue(member_user)
        token.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        token.save(update_fields=["expires_at"])
        assert not token.is_valid


class TestLoginAttempt:
    def test_recent_failures_counts_only_failures(self, member_user):
        for _ in range(3):
            LoginAttempt.objects.create(email=member_user.email, succeeded=False)
        LoginAttempt.objects.create(email=member_user.email, succeeded=True)
        assert LoginAttempt.recent_failures(member_user.email) == 3


class TestUserSession:
    def test_revoking_a_session_marks_it_inactive(self, member_user):
        session = UserSession.objects.create(
            user=member_user,
            jti="test-jti",
            expires_at=timezone.now() + timezone.timedelta(days=1),
        )
        assert session.is_active_session
        session.revoke()
        assert not session.is_active_session
