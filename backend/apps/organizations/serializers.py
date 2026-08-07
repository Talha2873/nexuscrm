"""Serializers for tenant management."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.constants import OrganizationRole
from apps.common.serializers import BaseModelSerializer, UserBriefSerializer
from apps.common.utils import normalise_email

from .models import (
    Department,
    Invitation,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    Team,
    TeamMembership,
)


class OrganizationSerializer(BaseModelSerializer):
    logo_url = serializers.SerializerMethodField()
    owner = UserBriefSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    seats_remaining = serializers.IntegerField(read_only=True)
    is_on_trial = serializers.BooleanField(read_only=True)
    is_subscription_active = serializers.BooleanField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Organization
        fields = (
            "id", "name", "slug", "legal_name", "description", "logo", "logo_url",
            "primary_color", "industry", "company_size", "website", "email", "phone",
            "address_line1", "address_line2", "city", "state", "postal_code",
            "country", "full_address", "timezone", "currency",
            "fiscal_year_start_month", "tax_number", "plan", "trial_ends_at",
            "subscription_ends_at", "max_users", "max_storage_mb", "is_active",
            "onboarding_completed", "owner", "member_count", "seats_remaining",
            "is_on_trial", "is_subscription_active", "my_role",
            "created_at", "updated_at", "created_by", "updated_by",
        )
        read_only_fields = (
            "id", "slug", "owner", "plan", "trial_ends_at", "subscription_ends_at",
            "max_users", "max_storage_mb", "created_at", "updated_at",
            "created_by", "updated_by",
        )
        extra_kwargs = {"logo": {"write_only": True, "required": False}}

    def get_logo_url(self, obj) -> str | None:
        if not obj.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url

    def get_my_role(self, obj) -> str | None:
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        membership = request.user.membership_for(obj)
        return membership.role if membership else None

    def validate_fiscal_year_start_month(self, value: int) -> int:
        if not 1 <= value <= 12:
            raise serializers.ValidationError("Enter a month between 1 and 12.")
        return value


class OrganizationCreateSerializer(serializers.Serializer):
    """Founding a new workspace from inside the app."""

    name = serializers.CharField(max_length=255)
    industry = serializers.ChoiceField(
        choices=Organization._meta.get_field("industry").choices, required=False
    )
    company_size = serializers.ChoiceField(
        choices=Organization._meta.get_field("company_size").choices, required=False
    )
    country = serializers.CharField(max_length=2, required=False, default="US")
    timezone = serializers.CharField(max_length=64, required=False, default="UTC")
    currency = serializers.ChoiceField(
        choices=Organization._meta.get_field("currency").choices, required=False, default="USD"
    )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please enter a workspace name.")
        return value


class OrganizationSettingsSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = OrganizationSettings
        fields = (
            "id", "ai_assistant_enabled", "lead_scoring_enabled",
            "email_notifications_enabled", "realtime_notifications_enabled",
            "audit_logging_enabled", "allow_public_signup",
            "require_email_verification", "two_factor_required",
            "default_deal_probability", "default_task_reminder_minutes",
            "ticket_sla_hours", "working_days", "working_hours_start",
            "working_hours_end", "email_signature", "webhook_url",
            "custom_fields_schema", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_default_deal_probability(self, value: int) -> int:
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Enter a probability between 0 and 100.")
        return value

    def validate_working_days(self, value: list) -> list:
        if not isinstance(value, list) or any(day not in range(1, 8) for day in value):
            raise serializers.ValidationError(
                "Working days must be a list of ISO weekday numbers (1=Monday .. 7=Sunday)."
            )
        return sorted(set(value))


class MembershipSerializer(BaseModelSerializer):
    user = UserBriefSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)
    is_email_verified = serializers.BooleanField(
        source="user.is_email_verified", read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = OrganizationMembership
        fields = (
            "id", "user", "role", "role_display", "title", "is_active",
            "joined_at", "department", "department_name", "last_login",
            "is_email_verified", "created_at", "updated_at",
        )
        read_only_fields = ("id", "user", "joined_at", "created_at", "updated_at")


class MembershipRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            (value, label)
            for value, label in OrganizationRole.choices
            if value != OrganizationRole.OWNER
        ]
    )


class DepartmentSerializer(BaseModelSerializer):
    head = UserBriefSerializer(read_only=True)
    head_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    member_count = serializers.IntegerField(read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta(BaseModelSerializer.Meta):
        model = Department
        fields = (
            "id", "name", "code", "description", "color", "head", "head_id",
            "parent", "parent_name", "member_count",
            "created_at", "updated_at", "created_by", "updated_by",
        )

    def validate(self, attrs: dict) -> dict:
        parent = attrs.get("parent")
        if parent and self.instance and parent.id == self.instance.id:
            raise serializers.ValidationError(
                {"parent": "A department cannot be its own parent."}
            )
        return attrs


class TeamMembershipSerializer(BaseModelSerializer):
    user = UserBriefSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = TeamMembership
        fields = ("id", "user", "role", "role_display", "is_active", "created_at")
        read_only_fields = ("id", "user", "created_at")


class TeamSerializer(BaseModelSerializer):
    lead = UserBriefSerializer(read_only=True)
    lead_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    member_count = serializers.IntegerField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    team_members = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Team
        fields = (
            "id", "name", "slug", "description", "color", "department",
            "department_name", "lead", "lead_id", "is_active", "member_count",
            "team_members", "created_at", "updated_at", "created_by", "updated_by",
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ("slug",)

    def get_team_members(self, obj) -> list:
        memberships = obj.team_memberships.filter(is_active=True).select_related("user")
        return TeamMembershipSerializer(memberships, many=True, context=self.context).data


class TeamMemberActionSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.ChoiceField(
        choices=TeamMembership.TeamRole.choices, required=False, default="member"
    )


class InvitationSerializer(BaseModelSerializer):
    invited_by = UserBriefSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Invitation
        fields = (
            "id", "email", "role", "role_display", "status", "status_display",
            "message", "expires_at", "accepted_at", "is_expired", "invited_by",
            "organization_name", "team", "department", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "status", "expires_at", "accepted_at", "invited_by",
            "created_at", "updated_at",
        )


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            (value, label)
            for value, label in OrganizationRole.choices
            if value != OrganizationRole.OWNER
        ],
        default=OrganizationRole.MEMBER,
    )
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    team = serializers.UUIDField(required=False, allow_null=True)
    department = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value: str) -> str:
        return normalise_email(value)


class InvitationBulkCreateSerializer(serializers.Serializer):
    invitations = InvitationCreateSerializer(many=True, allow_empty=False)


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()


class InvitationPreviewSerializer(serializers.Serializer):
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)
    role_display = serializers.CharField(read_only=True)
    organization_name = serializers.CharField(read_only=True)
    invited_by = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)


class TransferOwnershipSerializer(serializers.Serializer):
    new_owner_id = serializers.UUIDField()


class OrganizationStatsSerializer(serializers.Serializer):
    member_count = serializers.IntegerField()
    seats_total = serializers.IntegerField()
    seats_remaining = serializers.IntegerField()
    team_count = serializers.IntegerField()
    department_count = serializers.IntegerField()
    storage_used_bytes = serializers.IntegerField()
    storage_limit_bytes = serializers.IntegerField()
    plan = serializers.CharField()
    is_on_trial = serializers.BooleanField()
    trial_ends_at = serializers.DateTimeField(allow_null=True)
