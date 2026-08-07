"""Django admin for tenant models."""
from django.contrib import admin

from .models import (
    Department,
    Invitation,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    Team,
    TeamMembership,
)


class MembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 0
    raw_id_fields = ("user", "invited_by", "department")
    fields = ("user", "role", "title", "is_active", "department", "joined_at")
    readonly_fields = ("joined_at",)


class SettingsInline(admin.StackedInline):
    model = OrganizationSettings
    extra = 0
    can_delete = False
    fields = (
        "ai_assistant_enabled", "lead_scoring_enabled",
        "email_notifications_enabled", "realtime_notifications_enabled",
        "audit_logging_enabled", "require_email_verification",
        "default_deal_probability", "ticket_sla_hours",
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan", "owner", "member_count", "is_active", "created_at")
    list_filter = ("plan", "is_active", "industry", "company_size", "is_deleted")
    search_fields = ("name", "slug", "legal_name", "email")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("owner", "created_by", "updated_by", "deleted_by")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [SettingsInline, MembershipInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "legal_name", "description", "owner")}),
        ("Branding", {"fields": ("logo", "primary_color")}),
        ("Profile", {"fields": ("industry", "company_size", "website", "email", "phone")}),
        (
            "Address",
            {
                "fields": (
                    "address_line1", "address_line2", "city", "state",
                    "postal_code", "country",
                )
            },
        ),
        ("Locale", {"fields": ("timezone", "currency", "fiscal_year_start_month", "tax_number")}),
        (
            "Subscription",
            {
                "fields": (
                    "plan", "trial_ends_at", "subscription_ends_at",
                    "max_users", "max_storage_mb",
                )
            },
        ),
        ("Status", {"fields": ("is_active", "onboarding_completed", "is_deleted")}),
    )

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.member_count


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "department", "joined_at")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("user__email", "user__first_name", "user__last_name", "organization__name")
    raw_id_fields = ("user", "organization", "invited_by", "department")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "head", "parent", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "code", "description")
    raw_id_fields = ("organization", "head", "parent", "created_by", "updated_by")


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    raw_id_fields = ("user",)
    fields = ("user", "role", "is_active")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "department", "lead", "is_active", "created_at")
    list_filter = ("is_active", "organization", "department")
    search_fields = ("name", "description")
    raw_id_fields = ("organization", "lead", "department", "created_by", "updated_by")
    inlines = [TeamMembershipInline]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "role", "is_active")
    list_filter = ("role", "is_active")
    raw_id_fields = ("team", "user", "organization")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "status", "invited_by", "expires_at")
    list_filter = ("status", "role", "organization")
    search_fields = ("email", "organization__name")
    raw_id_fields = ("organization", "invited_by", "team", "department")
    readonly_fields = ("id", "token", "accepted_at", "created_at", "updated_at")


@admin.register(OrganizationSettings)
class OrganizationSettingsAdmin(admin.ModelAdmin):
    list_display = ("organization", "ai_assistant_enabled", "lead_scoring_enabled", "ticket_sla_hours")
    list_filter = ("ai_assistant_enabled", "lead_scoring_enabled")
    raw_id_fields = ("organization",)
