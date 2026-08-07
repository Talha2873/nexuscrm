"""Django admin registrations for shared models."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Activity, AuditLog, Document, Note, Tag, TaggedItem


class TenantAdminMixin:
    """Scopes the admin changelist to the staff user's own organizations."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=request.user,
            organization__memberships__is_active=True,
        ).distinct()


@admin.register(Tag)
class TagAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("name", "colour_swatch", "organization", "created_at")
    list_filter = ("organization", "created_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)

    @admin.display(description="Colour")
    def colour_swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:14px;height:14px;'
            'border-radius:3px;background:{};margin-right:6px;"></span>{}',
            obj.color,
            obj.color,
        )


@admin.register(Document)
class DocumentAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("name", "category", "organization", "uploaded_by", "file_size", "created_at")
    list_filter = ("category", "is_public", "organization", "created_at")
    search_fields = ("name", "description", "mime_type")
    readonly_fields = ("id", "file_size", "mime_type", "created_at", "updated_at")
    raw_id_fields = ("uploaded_by", "created_by", "updated_by", "deleted_by")


@admin.register(Note)
class NoteAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "author", "organization", "is_pinned", "created_at")
    list_filter = ("is_pinned", "organization", "created_at")
    search_fields = ("body",)
    raw_id_fields = ("author", "created_by", "updated_by", "deleted_by")


@admin.register(Activity)
class ActivityAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "actor", "verb", "target_repr", "organization")
    list_filter = ("verb", "organization", "created_at")
    search_fields = ("description", "target_repr")
    readonly_fields = tuple(f.name for f in Activity._meta.fields)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "actor_email", "action", "resource_type",
        "resource_repr", "status_code", "ip_address",
    )
    list_filter = ("action", "organization", "created_at")
    search_fields = ("actor_email", "resource_type", "resource_id", "request_path", "request_id")
    readonly_fields = tuple(f.name for f in AuditLog._meta.fields)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(TaggedItem)
class TaggedItemAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("tag", "content_type", "object_id", "organization", "created_at")
    list_filter = ("content_type", "organization")
    raw_id_fields = ("tag",)
