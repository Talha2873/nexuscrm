"""Serializers for every authentication endpoint."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.common.utils import normalise_email
from apps.common.validators import validate_strong_password

from .models import SocialAccount, UserSession

User = get_user_model()


# ---------------------------------------------------------------------------
# User representations
# ---------------------------------------------------------------------------
class OrganizationBriefSerializer(serializers.Serializer):
    """Minimal tenant payload embedded in auth responses."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj) -> str | None:
        logo = getattr(obj, "logo", None)
        if not logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(logo.url) if request else logo.url


class UserSerializer(serializers.ModelSerializer):
    """Full profile of the authenticated user."""

    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    active_organization = OrganizationBriefSerializer(read_only=True)
    organizations = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "full_name", "initials",
            "phone", "job_title", "bio", "avatar", "avatar_url", "timezone",
            "language", "theme", "is_active", "is_staff", "is_superuser",
            "is_email_verified", "two_factor_enabled", "active_organization",
            "organizations", "role", "date_joined", "last_login", "login_count",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "email", "is_active", "is_staff", "is_superuser",
            "is_email_verified", "date_joined", "last_login", "login_count",
            "created_at", "updated_at",
        )
        extra_kwargs = {"avatar": {"write_only": True, "required": False}}

    def get_avatar_url(self, obj) -> str:
        if obj.avatar:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return obj.avatar_url

    def get_organizations(self, obj) -> list:
        memberships = (
            obj.memberships.filter(is_active=True)
            .select_related("organization")
            .order_by("created_at")
        )
        return [
            {
                "id": str(membership.organization_id),
                "name": membership.organization.name,
                "slug": membership.organization.slug,
                "role": membership.role,
                "is_active": membership.organization.is_active,
            }
            for membership in memberships
        ]

    def get_role(self, obj) -> str | None:
        request = self.context.get("request")
        organization = getattr(request, "organization", None) if request else None
        organization = organization or obj.active_organization
        if organization is None:
            return None
        membership = obj.membership_for(organization)
        return membership.role if membership else None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Writable subset of the profile."""

    class Meta:
        model = User
        fields = (
            "first_name", "last_name", "phone", "job_title", "bio",
            "timezone", "language", "theme", "avatar",
        )

    def validate_first_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name is required.")
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=True)

    def validate_avatar(self, value):
        from apps.common.validators import validate_file_size

        validate_file_size(value)
        return value


# ---------------------------------------------------------------------------
# Registration & login
# ---------------------------------------------------------------------------
class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    organization_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True,
        help_text="Name of the workspace to create. Ignored when an invitation token is supplied.",
    )
    invitation_token = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Join an existing organization instead of creating one.",
    )
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    job_title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, default="UTC")

    def validate_email(self, value: str) -> str:
        value = normalise_email(value)
        if User.all_objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value: str) -> str:
        validate_strong_password(value)
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "The passwords do not match."})
        if not attrs.get("organization_name") and not attrs.get("invitation_token"):
            attrs["organization_name"] = ""
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value: str) -> str:
        return normalise_email(value)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    access_expires_in = serializers.IntegerField(read_only=True)
    refresh_expires_in = serializers.IntegerField(read_only=True)


class AuthResponseSerializer(serializers.Serializer):
    """Everything the SPA needs to bootstrap a session."""

    success = serializers.BooleanField(default=True)
    user = UserSerializer(read_only=True)
    organization = OrganizationBriefSerializer(read_only=True, allow_null=True)
    tokens = TokenPairSerializer(read_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)
    all_devices = serializers.BooleanField(default=False)


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(help_text="Google ID token returned by the client SDK.")


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return normalise_email(value)


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return normalise_email(value)


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_password(self, value: str) -> str:
        validate_strong_password(value)
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "The passwords do not match."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    new_password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_new_password(self, value: str) -> str:
        validate_strong_password(value)
        validate_password(value, user=self.context.get("request").user if self.context.get("request") else None)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs.pop("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "The passwords do not match."})
        return attrs


# ---------------------------------------------------------------------------
# Sessions & social accounts
# ---------------------------------------------------------------------------
class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = (
            "id", "device", "ip_address", "user_agent", "expires_at",
            "last_seen_at", "revoked_at", "is_current", "created_at",
        )
        read_only_fields = fields

    def get_is_current(self, obj) -> bool:
        return obj.jti == self.context.get("current_jti")


class SocialAccountSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = SocialAccount
        fields = ("id", "provider", "provider_display", "email", "last_used_at", "created_at")
        read_only_fields = fields


class SwitchOrganizationSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
