"""Authentication business logic."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.constants import AuditAction, OrganizationRole
from apps.common.exceptions import (
    BusinessRuleViolation,
    DuplicateResource,
    PermissionDeniedError,
    RateLimitExceeded,
    ResourceNotFound,
    ServiceError,
)
from apps.common.services import AuditService
from apps.common.utils import get_client_ip, get_user_agent, normalise_email

from .models import EmailVerificationToken, LoginAttempt, PasswordResetToken, UserSession
from .repositories import (
    EmailVerificationTokenRepository,
    LoginAttemptRepository,
    PasswordResetTokenRepository,
    SocialAccountRepository,
    UserRepository,
    UserSessionRepository,
)

logger = logging.getLogger(__name__)
User = get_user_model()

MAX_FAILED_ATTEMPTS = 8
LOCKOUT_WINDOW_MINUTES = 15


class AuthService:
    """Registration, login, tokens, verification and password management."""

    def __init__(self) -> None:
        self.users = UserRepository()
        self.verification_tokens = EmailVerificationTokenRepository()
        self.reset_tokens = PasswordResetTokenRepository()
        self.social = SocialAccountRepository()
        self.attempts = LoginAttemptRepository()
        self.sessions = UserSessionRepository()

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------
    def issue_tokens(self, user, request=None) -> dict:
        """Mint an access/refresh pair and record the session."""
        refresh = RefreshToken.for_user(user)
        refresh["email"] = user.email
        refresh["full_name"] = user.full_name
        if user.active_organization_id:
            refresh["organization_id"] = str(user.active_organization_id)

        lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
        UserSession.objects.create(
            user=user,
            jti=refresh["jti"],
            device=(get_user_agent(request)[:255] if request else ""),
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else "",
            expires_at=timezone.now() + lifetime,
        )

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "access_expires_in": int(
                settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
            ),
            "refresh_expires_in": int(lifetime.total_seconds()),
        }

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    @transaction.atomic
    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str = "",
        organization_name: str | None = None,
        invitation_token: str | None = None,
        request=None,
        **extra,
    ) -> dict:
        """Create a user and either found a new organization or accept an invite."""
        email = normalise_email(email)
        if self.users.email_exists(email):
            raise DuplicateResource("An account with this email already exists.")

        user = self.users.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            **extra,
        )

        organization = None
        if invitation_token:
            organization = self._accept_invitation(user, invitation_token)
        else:
            from apps.organizations.services import OrganizationService

            organization = OrganizationService().create_for_owner(
                owner=user,
                name=organization_name or f"{user.get_short_name()}'s workspace",
            )

        if organization is not None:
            self.users.set_active_organization(user, organization)

        token = EmailVerificationToken.issue(
            user, ip_address=get_client_ip(request) if request else None
        )

        from .tasks import send_verification_email

        send_verification_email.delay(str(user.id), token.token)

        AuditService.log(
            action=AuditAction.CREATE,
            resource_type="accounts.User",
            resource_id=user.pk,
            resource_repr=user.email,
            metadata={"flow": "registration"},
            actor=user,
            organization=organization,
            request=request,
        )

        return {"user": user, "organization": organization, "tokens": self.issue_tokens(user, request)}

    def _accept_invitation(self, user, invitation_token: str):
        from apps.organizations.services import InvitationService

        return InvitationService().accept(token=invitation_token, user=user)

    # ------------------------------------------------------------------
    # Login / logout
    # ------------------------------------------------------------------
    def login(self, email: str, password: str, request=None) -> dict:
        email = normalise_email(email)

        if LoginAttempt.recent_failures(email, LOCKOUT_WINDOW_MINUTES) >= MAX_FAILED_ATTEMPTS:
            self.attempts.record(email, False, request=request, reason="locked_out")
            raise RateLimitExceeded(
                "Too many failed attempts. Please try again in a few minutes."
            )

        user = authenticate(request, email=email, password=password)

        if user is None:
            existing = self.users.get_by_email(email)
            reason = "invalid_password" if existing else "unknown_email"
            if existing is not None and not existing.is_active:
                reason = "inactive_account"
            self.attempts.record(email, False, user=existing, request=request, reason=reason)
            raise ServiceError("Incorrect email or password.", code="invalid_credentials")

        self.attempts.record(email, True, user=user, request=request)

        user.login_count = (user.login_count or 0) + 1
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request) if request else None
        user.save(update_fields=["login_count", "last_login", "last_login_ip", "updated_at"])

        organization = user.active_organization
        if organization is None:
            organization = user.organizations().first()
            if organization is not None:
                self.users.set_active_organization(user, organization)

        return {
            "user": user,
            "organization": organization,
            "tokens": self.issue_tokens(user, request),
        }

    def logout(self, refresh_token: str, user=None) -> None:
        """Blacklist the refresh token and close the matching session."""
        try:
            token = RefreshToken(refresh_token)
            jti = token.get("jti")
            token.blacklist()
        except Exception as exc:  # invalid/expired token is not worth failing on
            logger.info("Logout with unusable refresh token: %s", exc)
            return

        if jti:
            UserSession.objects.filter(jti=jti, revoked_at__isnull=True).update(
                revoked_at=timezone.now()
            )

    def logout_all(self, user, except_jti: str | None = None) -> int:
        """Revoke every session for a user (used on password change)."""
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        blacklisted = 0
        for outstanding in OutstandingToken.objects.filter(user=user):
            if except_jti and outstanding.jti == except_jti:
                continue
            try:
                RefreshToken(outstanding.token).blacklist()
                blacklisted += 1
            except Exception:  # already blacklisted or expired
                continue

        self.sessions.revoke_all(user, except_jti=except_jti)
        return blacklisted

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------
    def verify_email(self, token: str):
        record = self.verification_tokens.get_valid(token)
        if record is None:
            raise ServiceError(
                "This verification link is invalid or has expired.",
                code="invalid_verification_token",
            )

        user = record.user
        if user.email != record.email:
            raise BusinessRuleViolation("This link was issued for a different address.")

        record.consume()
        self.users.mark_email_verified(user)

        AuditService.log(
            action=AuditAction.UPDATE,
            resource_type="accounts.User",
            resource_id=user.pk,
            resource_repr=user.email,
            metadata={"flow": "email_verification"},
            actor=user,
        )
        return user

    def resend_verification(self, email: str, request=None) -> None:
        """Always succeeds from the caller's point of view (no account enumeration)."""
        user = self.users.get_by_email(email)
        if user is None or user.is_email_verified:
            return

        token = EmailVerificationToken.issue(
            user, ip_address=get_client_ip(request) if request else None
        )
        from .tasks import send_verification_email

        send_verification_email.delay(str(user.id), token.token)

    # ------------------------------------------------------------------
    # Passwords
    # ------------------------------------------------------------------
    def request_password_reset(self, email: str, request=None) -> None:
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            logger.info("Password reset requested for unknown address")
            return

        token = PasswordResetToken.issue(
            user, ip_address=get_client_ip(request) if request else None
        )
        from .tasks import send_password_reset_email

        send_password_reset_email.delay(str(user.id), token.token)

    @transaction.atomic
    def reset_password(self, token: str, new_password: str, request=None):
        record = self.reset_tokens.get_valid(token)
        if record is None:
            raise ServiceError(
                "This password reset link is invalid or has expired.",
                code="invalid_reset_token",
            )

        user = record.user
        record.consume()
        self.users.set_password(user, new_password)
        self.logout_all(user)

        AuditService.log(
            action=AuditAction.PASSWORD_CHANGE,
            resource_type="accounts.User",
            resource_id=user.pk,
            resource_repr=user.email,
            metadata={"flow": "reset"},
            actor=user,
            request=request,
        )

        from .tasks import send_password_changed_email

        send_password_changed_email.delay(str(user.id))
        return user

    @transaction.atomic
    def change_password(self, user, current_password: str, new_password: str, request=None):
        if not user.check_password(current_password):
            raise ServiceError("Your current password is incorrect.", code="invalid_password")
        if current_password == new_password:
            raise BusinessRuleViolation("The new password must differ from the current one.")

        self.users.set_password(user, new_password)

        AuditService.log(
            action=AuditAction.PASSWORD_CHANGE,
            resource_type="accounts.User",
            resource_id=user.pk,
            resource_repr=user.email,
            metadata={"flow": "change"},
            actor=user,
            request=request,
        )

        from .tasks import send_password_changed_email

        send_password_changed_email.delay(str(user.id))
        return user

    # ------------------------------------------------------------------
    # Google OAuth
    # ------------------------------------------------------------------
    @transaction.atomic
    def google_login(self, id_token_str: str, request=None) -> dict:
        """Verify a Google ID token, then log in or provision the user."""
        claims = self._verify_google_token(id_token_str)

        email = normalise_email(claims.get("email", ""))
        if not email:
            raise ServiceError("Google did not return an email address.", code="google_no_email")
        if not claims.get("email_verified", False):
            raise ServiceError(
                "Your Google account email is not verified.", code="google_email_unverified"
            )

        provider_user_id = claims["sub"]
        account = self.social.get_for_provider("google", provider_user_id)
        created = False

        if account is not None:
            user = account.user
        else:
            user = self.users.get_by_email(email)
            if user is None:
                created = True
                user = self.users.create_user(
                    email=email,
                    password=None,
                    first_name=claims.get("given_name", "") or email.split("@")[0],
                    last_name=claims.get("family_name", ""),
                    is_email_verified=True,
                )
                from apps.organizations.services import OrganizationService

                organization = OrganizationService().create_for_owner(
                    owner=user, name=f"{user.get_short_name()}'s workspace"
                )
                self.users.set_active_organization(user, organization)

        self.social.link(
            user=user,
            provider="google",
            provider_user_id=provider_user_id,
            email=email,
            extra={
                "name": claims.get("name", ""),
                "picture": claims.get("picture", ""),
                "locale": claims.get("locale", ""),
            },
        )

        if not user.is_email_verified:
            self.users.mark_email_verified(user)
        if not user.is_active:
            raise PermissionDeniedError("This account has been deactivated.")

        user.login_count = (user.login_count or 0) + 1
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request) if request else None
        user.save(update_fields=["login_count", "last_login", "last_login_ip", "updated_at"])
        self.attempts.record(email, True, user=user, request=request)

        return {
            "user": user,
            "organization": user.active_organization,
            "created": created,
            "tokens": self.issue_tokens(user, request),
        }

    def _verify_google_token(self, id_token_str: str) -> dict:
        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        if not client_id:
            raise ServiceError(
                "Google sign-in is not configured on this server.",
                code="google_not_configured",
            )
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            return google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), client_id
            )
        except ValueError as exc:
            logger.info("Rejected Google ID token: %s", exc)
            raise ServiceError("Invalid Google credentials.", code="invalid_google_token") from exc

    # ------------------------------------------------------------------
    # Organization switching
    # ------------------------------------------------------------------
    def switch_organization(self, user, organization_id):
        membership = user.membership_for(organization_id)
        if membership is None:
            raise PermissionDeniedError("You are not a member of that organization.")
        self.users.set_active_organization(user, membership.organization)
        return membership.organization

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def list_sessions(self, user):
        return self.sessions.active_for_user(user)

    def revoke_session(self, user, session_id):
        session = self.sessions.get_queryset().filter(id=session_id, user=user).first()
        if session is None:
            raise ResourceNotFound("Session not found.")
        session.revoke()
        return session


class ProfileService:
    """Updates to the caller's own profile."""

    def __init__(self) -> None:
        self.users = UserRepository()

    @transaction.atomic
    def update_profile(self, user, **payload):
        allowed = {
            "first_name", "last_name", "phone", "job_title", "bio",
            "timezone", "language", "theme", "avatar",
        }
        updates = {key: value for key, value in payload.items() if key in allowed}
        for field, value in updates.items():
            setattr(user, field, value)
        if updates:
            user.save(update_fields=[*updates.keys(), "updated_at"])
        return user

    def deactivate(self, user):
        if user.organizations().filter(memberships__role=OrganizationRole.OWNER).exists():
            raise BusinessRuleViolation(
                "Transfer ownership of your organizations before deactivating your account."
            )
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        AuthService().logout_all(user)
        return user

    def cleanup_expired_tokens(self) -> int:
        """Delete verification/reset tokens that expired more than a week ago."""
        cutoff = timezone.now() - timedelta(days=7)
        deleted = 0
        for model in (EmailVerificationToken, PasswordResetToken):
            count, _ = model.all_objects.filter(expires_at__lt=cutoff).delete()
            deleted += count
        return deleted
