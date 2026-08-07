"""Endpoints for tenant, membership, team, department and invitation management."""
from __future__ import annotations

from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import (
    IsManagerOrAbove,
    IsOrganizationAdmin,
    IsOrganizationMember,
    IsOrganizationOwner,
)
from apps.common.serializers import ErrorResponseSerializer, SuccessResponseSerializer
from apps.common.viewsets import BaseViewSet

from .filters import DepartmentFilter, InvitationFilter, MembershipFilter, TeamFilter
from .models import Department, Invitation, Organization, OrganizationMembership, Team
from .serializers import (
    AcceptInvitationSerializer,
    DepartmentSerializer,
    InvitationBulkCreateSerializer,
    InvitationCreateSerializer,
    InvitationPreviewSerializer,
    InvitationSerializer,
    MembershipRoleUpdateSerializer,
    MembershipSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
    OrganizationSettingsSerializer,
    OrganizationStatsSerializer,
    TeamMemberActionSerializer,
    TeamSerializer,
    TransferOwnershipSerializer,
)
from .services import (
    DepartmentService,
    InvitationService,
    MembershipService,
    OrganizationService,
    TeamService,
)


@extend_schema(tags=["Organizations"])
@extend_schema_view(
    list=extend_schema(summary="List the organizations you belong to"),
    retrieve=extend_schema(summary="Get one organization"),
    update=extend_schema(summary="Replace organization details"),
    partial_update=extend_schema(summary="Update organization details"),
)
class OrganizationViewSet(BaseViewSet):
    """The tenants the signed-in user is a member of."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "legal_name", "slug", "email"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    audit_resource_type = "organizations.Organization"
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        """Organizations are not organization-scoped; scope by membership instead."""
        user = self.request.user
        queryset = Organization.objects.all().select_related("owner")
        if user.is_superuser:
            return queryset
        return queryset.filter(
            memberships__user=user, memberships__is_active=True
        ).distinct()

    def get_permissions(self):
        if self.action in {"update", "partial_update", "settings", "stats"}:
            return [IsAuthenticated(), IsOrganizationMember(), IsOrganizationAdmin()]
        if self.action in {"transfer_ownership"}:
            return [IsAuthenticated(), IsOrganizationMember(), IsOrganizationOwner()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Create an additional organization",
        request=OrganizationCreateSerializer,
        responses={201: OrganizationSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = OrganizationService().create_for_owner(
            owner=request.user, **serializer.validated_data
        )
        return Response(
            OrganizationSerializer(organization, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        OrganizationService().update_organization(
            serializer.instance, self.request.user, **serializer.validated_data
        )
        return serializer.instance

    @extend_schema(
        summary="Get the current organization",
        responses={200: OrganizationSerializer, 404: ErrorResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def current(self, request):
        organization = getattr(request, "organization", None)
        if organization is None:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "organization_required",
                        "message": "You do not have an active organization.",
                        "details": {},
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            OrganizationSerializer(organization, context=self.get_serializer_context()).data
        )

    @extend_schema(
        summary="Read or update organization settings",
        request=OrganizationSettingsSerializer,
        responses={200: OrganizationSettingsSerializer},
    )
    @action(detail=True, methods=["get", "patch"])
    def settings(self, request, pk=None):
        organization = self.get_object()
        service = OrganizationService()

        if request.method == "PATCH":
            serializer = OrganizationSettingsSerializer(
                service.get_settings(organization), data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            updated = service.update_settings(
                organization, request.user, **serializer.validated_data
            )
            return Response(OrganizationSettingsSerializer(updated).data)

        return Response(OrganizationSettingsSerializer(service.get_settings(organization)).data)

    @extend_schema(summary="Organization usage statistics", responses={200: OrganizationStatsSerializer})
    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        organization = self.get_object()
        return Response(OrganizationService().statistics(organization))

    @extend_schema(
        summary="Transfer ownership to another member",
        request=TransferOwnershipSerializer,
        responses={200: OrganizationSerializer, 403: ErrorResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="transfer-ownership")
    def transfer_ownership(self, request, pk=None):
        organization = self.get_object()
        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = OrganizationService().transfer_ownership(
            organization, request.user, serializer.validated_data["new_owner_id"]
        )
        return Response(
            OrganizationSerializer(organization, context=self.get_serializer_context()).data
        )

    @extend_schema(summary="Mark onboarding as complete", request=None, responses={200: OrganizationSerializer})
    @action(detail=True, methods=["post"], url_path="complete-onboarding")
    def complete_onboarding(self, request, pk=None):
        organization = self.get_object()
        organization.onboarding_completed = True
        organization.save(update_fields=["onboarding_completed", "updated_at"])
        return Response(
            OrganizationSerializer(organization, context=self.get_serializer_context()).data
        )

    @extend_schema(summary="Leave this organization", request=None, responses={200: SuccessResponseSerializer})
    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        organization = self.get_object()
        MembershipService().leave(organization, request.user)
        return Response({"success": True, "message": "You have left the organization."})


@extend_schema(tags=["Organizations"])
@extend_schema_view(
    list=extend_schema(summary="List members of the organization"),
    retrieve=extend_schema(summary="Get one membership"),
    partial_update=extend_schema(summary="Update a member's title or department"),
    destroy=extend_schema(summary="Remove a member from the organization"),
)
class MembershipViewSet(BaseViewSet):
    """Who belongs to the current organization."""

    queryset = OrganizationMembership.objects.all()
    serializer_class = MembershipSerializer
    filterset_class = MembershipFilter
    search_fields = ["user__email", "user__first_name", "user__last_name", "title"]
    ordering_fields = ["created_at", "role", "user__first_name"]
    ordering = ["-created_at"]
    select_related_fields = ("user", "department", "organization")
    audit_resource_type = "organizations.OrganizationMembership"
    http_method_names = ["get", "patch", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in {"list", "retrieve", "me"}:
            return [IsAuthenticated(), IsOrganizationMember()]
        return [IsAuthenticated(), IsOrganizationMember(), IsOrganizationAdmin()]

    @extend_schema(summary="Your own membership", responses={200: MembershipSerializer})
    @action(detail=False, methods=["get"])
    def me(self, request):
        membership = getattr(request, "membership", None)
        if membership is None:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "not_found",
                        "message": "You have no membership in this organization.",
                        "details": {},
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            MembershipSerializer(membership, context=self.get_serializer_context()).data
        )

    @extend_schema(
        summary="Change a member's role",
        request=MembershipRoleUpdateSerializer,
        responses={200: MembershipSerializer, 403: ErrorResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="change-role")
    def change_role(self, request, pk=None):
        membership = self.get_object()
        serializer = MembershipRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = MembershipService().change_role(
            membership, request.user, serializer.validated_data["role"]
        )
        return Response(
            MembershipSerializer(membership, context=self.get_serializer_context()).data
        )

    @extend_schema(summary="Reactivate a removed member", request=None, responses={200: MembershipSerializer})
    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        membership = MembershipService().reactivate(self.get_object(), request.user)
        return Response(
            MembershipSerializer(membership, context=self.get_serializer_context()).data
        )

    def perform_destroy(self, instance):
        MembershipService().deactivate(instance, self.request.user)


@extend_schema(tags=["Organizations"])
class DepartmentViewSet(BaseViewSet):
    """Departments within the organization."""

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    filterset_class = DepartmentFilter
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    select_related_fields = ("head", "parent")
    audit_resource_type = "organizations.Department"

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated(), IsOrganizationMember()]
        return [IsAuthenticated(), IsOrganizationMember(), IsManagerOrAbove()]

    def get_queryset(self):
        return super().get_queryset().annotate(
            member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
        )

    def perform_destroy(self, instance):
        DepartmentService().delete(instance)


@extend_schema(tags=["Organizations"])
class TeamViewSet(BaseViewSet):
    """Teams within the organization."""

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    filterset_class = TeamFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    select_related_fields = ("lead", "department")
    prefetch_related_fields = ("team_memberships__user",)
    audit_resource_type = "organizations.Team"

    def get_permissions(self):
        if self.action in {"list", "retrieve", "my_teams"}:
            return [IsAuthenticated(), IsOrganizationMember()]
        return [IsAuthenticated(), IsOrganizationMember(), IsManagerOrAbove()]

    def get_queryset(self):
        return super().get_queryset().annotate(
            member_count=Count(
                "team_memberships",
                filter=Q(team_memberships__is_active=True),
                distinct=True,
            )
        )

    @extend_schema(summary="Teams you belong to", responses={200: TeamSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="my-teams")
    def my_teams(self, request):
        queryset = self.get_queryset().filter(
            team_memberships__user=request.user, team_memberships__is_active=True
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"success": True, "results": serializer.data})

    @extend_schema(
        summary="Add a member to the team",
        request=TeamMemberActionSerializer,
        responses={201: TeamSerializer},
    )
    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        team = self.get_object()
        serializer = TeamMemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        TeamService().add_member(
            team,
            serializer.validated_data["user_id"],
            serializer.validated_data.get("role", "member"),
        )
        team.refresh_from_db()
        return Response(
            TeamSerializer(team, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Remove a member from the team",
        request=TeamMemberActionSerializer,
        responses={200: SuccessResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="remove-member")
    def remove_member(self, request, pk=None):
        team = self.get_object()
        serializer = TeamMemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        TeamService().remove_member(team, serializer.validated_data["user_id"])
        return Response({"success": True, "message": "Member removed from the team."})


@extend_schema(tags=["Organizations"])
class InvitationViewSet(BaseViewSet):
    """Invite people into the organization and manage pending invitations."""

    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer
    filterset_class = InvitationFilter
    search_fields = ["email", "message"]
    ordering_fields = ["created_at", "expires_at", "status"]
    ordering = ["-created_at"]
    select_related_fields = ("invited_by", "organization", "team", "department")
    audit_resource_type = "organizations.Invitation"
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        return [IsAuthenticated(), IsOrganizationMember(), IsManagerOrAbove()]

    @extend_schema(
        summary="Invite someone to the organization",
        request=InvitationCreateSerializer,
        responses={201: InvitationSerializer, 409: ErrorResponseSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        team = (
            Team.objects.filter(
                id=data.get("team"), organization=request.organization
            ).first()
            if data.get("team")
            else None
        )
        department = (
            Department.objects.filter(
                id=data.get("department"), organization=request.organization
            ).first()
            if data.get("department")
            else None
        )

        invitation = InvitationService().invite(
            organization=request.organization,
            inviter=request.user,
            email=data["email"],
            role=data["role"],
            message=data.get("message", ""),
            team=team,
            department=department,
        )
        return Response(
            InvitationSerializer(invitation, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Invite several people at once",
        request=InvitationBulkCreateSerializer,
        responses={201: InvitationSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk_invite(self, request):
        serializer = InvitationBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = InvitationService()
        created, failed = [], []
        for payload in serializer.validated_data["invitations"]:
            try:
                invitation = service.invite(
                    organization=request.organization,
                    inviter=request.user,
                    email=payload["email"],
                    role=payload["role"],
                    message=payload.get("message", ""),
                )
                created.append(invitation)
            except Exception as exc:  # collect per-row failures, keep going
                failed.append({"email": payload["email"], "error": str(exc)})

        return Response(
            {
                "success": True,
                "created": InvitationSerializer(
                    created, many=True, context=self.get_serializer_context()
                ).data,
                "failed": failed,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Resend an invitation email", request=None, responses={200: InvitationSerializer})
    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        invitation = InvitationService().resend(self.get_object(), request.user)
        return Response(
            InvitationSerializer(invitation, context=self.get_serializer_context()).data
        )

    @extend_schema(summary="Revoke a pending invitation", request=None, responses={200: InvitationSerializer})
    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        invitation = InvitationService().revoke(self.get_object(), request.user)
        return Response(
            InvitationSerializer(invitation, context=self.get_serializer_context()).data
        )


@extend_schema(tags=["Organizations"])
class InvitationPreviewView(APIView):
    """Public: show who invited you and to which organization, before signing up."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        summary="Preview an invitation by token",
        responses={200: InvitationPreviewSerializer, 404: ErrorResponseSerializer},
    )
    def get(self, request, token):
        return Response({"success": True, **InvitationService().preview(token)})


@extend_schema(tags=["Organizations"])
class AcceptInvitationView(APIView):
    """Accept an invitation as the signed-in user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Accept an invitation",
        request=AcceptInvitationSerializer,
        responses={200: OrganizationSerializer, 403: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = InvitationService().accept(
            token=serializer.validated_data["token"], user=request.user
        )
        return Response(
            {
                "success": True,
                "message": f"You have joined {organization.name}.",
                "organization": OrganizationSerializer(
                    organization, context={"request": request}
                ).data,
            }
        )
