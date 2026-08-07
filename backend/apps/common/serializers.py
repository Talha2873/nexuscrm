"""Serializer base classes and small reusable serializers."""
from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .context import get_current_organization
from .models import Activity, AuditLog, Document, Note, Tag, TaggedItem
from .utils import human_file_size


class TimestampedSerializerMixin(serializers.Serializer):
    """Adds the audit columns every model exposes, all read-only."""

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UserBriefSerializer(serializers.Serializer):
    """Compact user representation embedded in other payloads."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj) -> str | None:
        avatar = getattr(obj, "avatar", None)
        if avatar:
            request = self.context.get("request")
            url = avatar.url
            return request.build_absolute_uri(url) if request else url
        from .utils import gravatar_url

        return gravatar_url(getattr(obj, "email", ""))


class BaseModelSerializer(serializers.ModelSerializer):
    """Shared behaviour for every model serializer.

    * Stamps ``organization`` from the request context on create.
    * Exposes ``created_by``/``updated_by`` as nested briefs, never writable.
    * Lets views request a subset of fields with ``?fields=id,name``.
    """

    created_by = UserBriefSerializer(read_only=True)
    updated_by = UserBriefSerializer(read_only=True)

    class Meta:
        abstract = True
        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "is_deleted",
            "deleted_at",
        )

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if fields is None and request is not None:
            requested = request.query_params.get("fields")
            fields = [f.strip() for f in requested.split(",")] if requested else None

        if fields:
            allowed = set(fields) | {"id"}
            for field_name in set(self.fields) - allowed:
                self.fields.pop(field_name, None)

    def create(self, validated_data: dict[str, Any]):
        model = self.Meta.model
        if any(f.name == "organization" for f in model._meta.fields):
            validated_data.setdefault("organization", get_current_organization())
        return super().create(validated_data)


class TagSerializer(BaseModelSerializer):
    usage_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(BaseModelSerializer.Meta):
        model = Tag
        fields = (
            "id", "name", "slug", "color", "description", "usage_count",
            "created_at", "updated_at", "created_by", "updated_by",
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ("slug", "usage_count")

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Tag name cannot be empty.")
        queryset = Tag.objects.filter(
            organization=get_current_organization(), name__iexact=value
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A tag with this name already exists.")
        return value


class GenericRelationSerializerMixin(serializers.Serializer):
    """Accepts ``content_type`` as a model label such as ``deals.deal``."""

    content_type = serializers.CharField(required=False, allow_null=True)
    object_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_content_type(self, value: str | None):
        if not value:
            return None
        try:
            app_label, model = value.lower().split(".")
            return ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist) as exc:
            raise serializers.ValidationError(
                "Use '<app_label>.<model>', e.g. 'deals.deal'."
            ) from exc


class DocumentSerializer(GenericRelationSerializerMixin, BaseModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    extension = serializers.CharField(read_only=True)
    uploaded_by = UserBriefSerializer(read_only=True)
    content_type_label = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Document
        fields = (
            "id", "name", "description", "file", "file_url", "category",
            "file_size", "file_size_display", "mime_type", "extension",
            "is_public", "version", "content_type", "content_type_label",
            "object_id", "uploaded_by", "created_at", "updated_at",
            "created_by", "updated_by",
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + (
            "file_size", "mime_type", "uploaded_by", "version",
        )
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def get_file_size_display(self, obj) -> str:
        return human_file_size(obj.file_size)

    def get_content_type_label(self, obj) -> str | None:
        if not obj.content_type_id:
            return None
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class NoteSerializer(GenericRelationSerializerMixin, BaseModelSerializer):
    author = UserBriefSerializer(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Note
        fields = (
            "id", "body", "is_pinned", "content_type", "object_id", "author",
            "created_at", "updated_at", "created_by", "updated_by",
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ("author",)

    def validate_body(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("A note cannot be empty.")
        return value.strip()


class ActivitySerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)
    verb_display = serializers.CharField(source="get_verb_display", read_only=True)
    content_type_label = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = (
            "id", "verb", "verb_display", "description", "metadata", "actor",
            "content_type", "content_type_label", "object_id", "target_repr",
            "created_at",
        )
        read_only_fields = fields

    def get_content_type_label(self, obj) -> str | None:
        if not obj.content_type_id:
            return None
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class AuditLogSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id", "actor", "actor_email", "action", "action_display",
            "resource_type", "resource_id", "resource_repr", "changes",
            "metadata", "ip_address", "user_agent", "request_id",
            "request_method", "request_path", "status_code", "created_at",
        )
        read_only_fields = fields


class TaggedItemSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)

    class Meta:
        model = TaggedItem
        fields = ("id", "tag", "content_type", "object_id", "created_at")
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Utility serializers (request/response shapes that have no model)
# ---------------------------------------------------------------------------
class SuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    error = ErrorDetailSerializer()
    request_id = serializers.CharField(allow_null=True, required=False)


class BulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, max_length=500
    )


class BulkActionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    affected = serializers.IntegerField()
    message = serializers.CharField()


class GlobalSearchResultSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.UUIDField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    url = serializers.CharField()
    score = serializers.FloatField(required=False)


class GlobalSearchResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    query = serializers.CharField()
    total = serializers.IntegerField()
    results = GlobalSearchResultSerializer(many=True)
