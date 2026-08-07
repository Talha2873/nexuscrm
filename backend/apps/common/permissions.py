"""Permission classes.

Two layers guard every endpoint:

1. **Tenant membership** - the caller must belong to the active organization.
2. **Role / capability** - the caller's role must grant the required action.
"""
from __future__ import annotations

from rest_framework import permissions

from .constants import ROLE_HIERARCHY, OrganizationRole


def _membership(request):
    """Return the caller's membership of the active organization, or ``None``."""
    return getattr(request, "membership", None)


def _role(request) -> str | None:
    membership = _membership(request)
    return getattr(membership, "role", None)


def _role_rank(request) -> int:
    return ROLE_HIERARCHY.get(_role(request), 0)


class IsAuthenticatedAndVerified(permissions.BasePermission):
    """Authenticated *and* email-verified (superusers bypass verification)."""

    message = "Please verify your email address to continue."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        return bool(getattr(user, "is_email_verified", False))


class IsOrganizationMember(permissions.BasePermission):
    """Caller must have an active membership of the resolved organization."""

    message = "You are not a member of this organization."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        organization = getattr(request, "organization", None)
        membership = _membership(request)
        return bool(organization and membership and membership.is_active)

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_superuser:
            return True
        organization = getattr(request, "organization", None)
        object_org_id = getattr(obj, "organization_id", None)
        if object_org_id is None:
            return True
        return organization is not None and object_org_id == organization.id


class HasRoleAtLeast(permissions.BasePermission):
    """Require a minimum role in the hierarchy.

    Set ``required_role`` on the view, or subclass with a fixed role.
    """

    required_role: str = OrganizationRole.VIEWER
    message = "Your role does not allow this action."

    def has_permission(self, request, view) -> bool:
        if request.user.is_superuser:
            return True
        required = getattr(view, "required_role", self.required_role)
        return _role_rank(request) >= ROLE_HIERARCHY.get(required, 0)


class IsOrganizationOwner(HasRoleAtLeast):
    required_role = OrganizationRole.OWNER
    message = "Only the organization owner can perform this action."


class IsOrganizationAdmin(HasRoleAtLeast):
    required_role = OrganizationRole.ADMIN
    message = "Only administrators can perform this action."


class IsManagerOrAbove(HasRoleAtLeast):
    required_role = OrganizationRole.MANAGER
    message = "Only managers and above can perform this action."


class IsMemberOrAbove(HasRoleAtLeast):
    required_role = OrganizationRole.MEMBER
    message = "Viewers cannot modify records."


class ReadOnlyForViewers(permissions.BasePermission):
    """Viewers may read everything but write nothing."""

    message = "Your role is read-only."

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        return _role(request) != OrganizationRole.VIEWER


class IsOwnerOrManager(permissions.BasePermission):
    """Object-level: the record's owner/assignee, or a manager and above."""

    message = "You can only modify records assigned to you."
    owner_fields = ("owner_id", "assigned_to_id", "created_by_id", "user_id")

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        if _role_rank(request) >= ROLE_HIERARCHY[OrganizationRole.MANAGER]:
            return True
        user_id = request.user.id
        for field in getattr(view, "owner_fields", self.owner_fields):
            if getattr(obj, field, None) == user_id:
                return True
        return False


class IsSelfOrAdmin(permissions.BasePermission):
    """Users may edit their own profile; admins may edit anyone's."""

    message = "You can only modify your own profile."

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_superuser:
            return True
        if _role_rank(request) >= ROLE_HIERARCHY[OrganizationRole.ADMIN]:
            return True
        target_user_id = getattr(obj, "user_id", None) or getattr(obj, "id", None)
        return target_user_id == request.user.id


class HasCapability(permissions.BasePermission):
    """Fine-grained capability check against the user's assigned roles.

    Views declare ``required_capability = "deals.delete"``; the capability is
    looked up on the user's :class:`apps.users.models.Role` objects.
    """

    message = "You lack the required permission for this action."

    def has_permission(self, request, view) -> bool:
        capability = getattr(view, "required_capability", None)
        if capability is None:
            return True
        if request.user.is_superuser:
            return True
        if _role_rank(request) >= ROLE_HIERARCHY[OrganizationRole.ADMIN]:
            return True
        checker = getattr(request.user, "has_capability", None)
        return bool(checker and checker(capability, organization=getattr(request, "organization", None)))


class AllowAnyReadAuthenticatedWrite(permissions.BasePermission):
    """Public reads (e.g. shared invoice link), authenticated writes."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
