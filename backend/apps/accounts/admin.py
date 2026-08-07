"""Django admin for authentication models."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import (
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    SocialAccount,
    User,
    UserSession,
)


class NexusUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class NexusUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = NexusUserCreationForm
    form = NexusUserChangeForm
    change_password_form = AdminPasswordChangeForm
    model = User

    list_display = (
        "email", "full_name", "active_organization", "is_active",
        "is_email_verified", "is_staff", "last_login",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "is_email_verified", "is_deleted")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("email",)
    readonly_fields = ("id", "date_joined", "last_login", "login_count", "last_login_ip", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone", "job_title", "bio", "avatar")}),
        (_("Preferences"), {"fields": ("timezone", "language", "theme")}),
        (_("Tenancy"), {"fields": ("active_organization",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active", "is_staff", "is_superuser", "is_email_verified",
                    "two_factor_enabled", "groups", "user_permissions",
                )
            },
        ),
        (_("Telemetry"), {"fields": ("last_login", "date_joined", "login_count", "last_login_ip", "last_active_at")}),
        (_("Soft delete"), {"fields": ("is_deleted", "deleted_at", "deleted_by")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.full_name


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "expires_at", "used_at", "created_at")
    list_filter = ("created_at",)
    search_fields = ("email", "token")
    readonly_fields = ("id", "token", "created_at", "updated_at")
    raw_id_fields = ("user",)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "token")
    readonly_fields = ("id", "token", "created_at", "updated_at")
    raw_id_fields = ("user",)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "email", "last_used_at", "created_at")
    list_filter = ("provider",)
    search_fields = ("user__email", "email", "provider_user_id")
    raw_id_fields = ("user",)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email", "succeeded", "failure_reason", "ip_address")
    list_filter = ("succeeded", "created_at")
    search_fields = ("email", "ip_address")
    readonly_fields = tuple(f.name for f in LoginAttempt._meta.fields)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device", "ip_address", "last_seen_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at", "created_at")
    search_fields = ("user__email", "device", "ip_address", "jti")
    raw_id_fields = ("user",)
    readonly_fields = ("id", "jti", "created_at", "updated_at")
