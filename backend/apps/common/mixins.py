"""Reusable ViewSet mixins."""
from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .constants import AuditAction
from .serializers import (
    ActivitySerializer,
    BulkActionResponseSerializer,
    BulkIdsSerializer,
    DocumentSerializer,
    NoteSerializer,
    SuccessResponseSerializer,
)
from .services import ActivityService, AuditService


class MultiSerializerMixin:
    """Pick a serializer per action via ``serializer_classes``.

    ::

        serializer_classes = {
            "list": DealListSerializer,
            "retrieve": DealDetailSerializer,
        }
    """

    serializer_classes: dict = {}

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, super().get_serializer_class())


class AuditMixin:
    """Write an audit record for every mutating action."""

    audit_resource_type: str = ""

    def _resource_type(self) -> str:
        if self.audit_resource_type:
            return self.audit_resource_type
        queryset = getattr(self, "queryset", None)
        if queryset is not None:
            return queryset.model._meta.label
        return self.__class__.__name__

    def get_save_kwargs(self) -> dict:
        """Extra kwargs injected into ``serializer.save()``.

        Concrete viewsets override this to stamp relations that come from the
        request rather than the payload (uploader, author, organization).
        """
        return {}

    def perform_create(self, serializer):
        instance = serializer.save(**self.get_save_kwargs())
        AuditService.log(
            action=AuditAction.CREATE,
            resource_type=self._resource_type(),
            resource_id=instance.pk,
            resource_repr=str(instance),
            changes={"created": serializer.data},
            request=self.request,
        )
        return instance

    def perform_update(self, serializer):
        from .utils import diff_snapshots, model_to_snapshot

        before = model_to_snapshot(serializer.instance)
        instance = serializer.save()
        after = model_to_snapshot(instance)
        AuditService.log(
            action=AuditAction.UPDATE,
            resource_type=self._resource_type(),
            resource_id=instance.pk,
            resource_repr=str(instance),
            changes=diff_snapshots(before, after),
            request=self.request,
        )
        return instance

    def perform_destroy(self, instance):
        AuditService.log(
            action=AuditAction.DELETE,
            resource_type=self._resource_type(),
            resource_id=instance.pk,
            resource_repr=str(instance),
            request=self.request,
        )
        instance.delete()


class SoftDeleteMixin:
    """Adds ``POST /{id}/restore/`` and ``DELETE /{id}/?hard=true``."""

    @extend_schema(
        summary="Restore a soft-deleted record",
        responses={200: SuccessResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def restore(self, request, *args, **kwargs):
        queryset = self.get_queryset().model.all_objects.filter(
            pk=kwargs.get("pk"), organization=request.organization
        )
        instance = queryset.first()
        if instance is None:
            return Response(
                {"success": False, "error": {"code": "not_found", "message": "Record not found.", "details": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        instance.restore()
        return Response({"success": True, "message": "Record restored successfully."})

    def perform_destroy(self, instance):
        hard = str(self.request.query_params.get("hard", "")).lower() in {"1", "true", "yes"}
        if hard and self.request.user.is_superuser:
            instance.delete(hard=True)
        else:
            instance.delete()


class BulkActionMixin:
    """Adds ``POST /bulk-delete/`` and ``POST /bulk-restore/``."""

    @extend_schema(
        summary="Delete several records at once",
        request=BulkIdsSerializer,
        responses={200: BulkActionResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        with transaction.atomic():
            queryset = self.get_queryset().filter(pk__in=ids)
            affected = queryset.count()
            for instance in queryset:
                AuditService.log(
                    action=AuditAction.DELETE,
                    resource_type=instance._meta.label,
                    resource_id=instance.pk,
                    resource_repr=str(instance),
                    request=request,
                )
                instance.delete()

        return Response(
            {
                "success": True,
                "affected": affected,
                "message": f"{affected} record(s) deleted.",
            }
        )

    @extend_schema(
        summary="Restore several soft-deleted records at once",
        request=BulkIdsSerializer,
        responses={200: BulkActionResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        model = self.get_queryset().model
        affected = model.all_objects.filter(
            pk__in=ids, organization=request.organization, is_deleted=True
        ).update(is_deleted=False, deleted_at=None)

        return Response(
            {
                "success": True,
                "affected": affected,
                "message": f"{affected} record(s) restored.",
            }
        )


class TimelineMixin:
    """Adds ``GET /{id}/activities/`` returning that record's timeline."""

    @extend_schema(
        summary="Activity timeline for this record",
        responses={200: ActivitySerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def activities(self, request, *args, **kwargs):
        instance = self.get_object()
        queryset = ActivityService.for_object(instance)
        page = self.paginate_queryset(queryset)
        serializer = ActivitySerializer(
            page if page is not None else queryset, many=True, context=self.get_serializer_context()
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"success": True, "results": serializer.data})


class AttachmentMixin:
    """Adds ``GET|POST /{id}/documents/`` and ``GET|POST /{id}/notes/``."""

    @extend_schema(
        summary="List or upload documents attached to this record",
        request=DocumentSerializer,
        responses={200: DocumentSerializer(many=True), 201: DocumentSerializer},
    )
    @action(detail=True, methods=["get", "post"], parser_classes=[])
    def documents(self, request, *args, **kwargs):
        from django.contrib.contenttypes.models import ContentType

        from .models import Document

        instance = self.get_object()
        content_type = ContentType.objects.get_for_model(instance.__class__)

        if request.method == "POST":
            serializer = DocumentSerializer(
                data=request.data, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(
                organization=request.organization,
                content_type=content_type,
                object_id=instance.pk,
                uploaded_by=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = Document.objects.filter(
            organization=request.organization,
            content_type=content_type,
            object_id=instance.pk,
        ).select_related("uploaded_by")
        serializer = DocumentSerializer(
            queryset, many=True, context=self.get_serializer_context()
        )
        return Response({"success": True, "results": serializer.data})

    @extend_schema(
        summary="List or add notes attached to this record",
        request=NoteSerializer,
        responses={200: NoteSerializer(many=True), 201: NoteSerializer},
    )
    @action(detail=True, methods=["get", "post"])
    def notes(self, request, *args, **kwargs):
        from django.contrib.contenttypes.models import ContentType

        from .models import Note

        instance = self.get_object()
        content_type = ContentType.objects.get_for_model(instance.__class__)

        if request.method == "POST":
            serializer = NoteSerializer(
                data=request.data, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(
                organization=request.organization,
                content_type=content_type,
                object_id=instance.pk,
                author=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = Note.objects.filter(
            organization=request.organization,
            content_type=content_type,
            object_id=instance.pk,
        ).select_related("author")
        serializer = NoteSerializer(
            queryset, many=True, context=self.get_serializer_context()
        )
        return Response({"success": True, "results": serializer.data})
