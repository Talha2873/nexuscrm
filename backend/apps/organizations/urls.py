"""Organization routes, mounted at /api/v1/organizations/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcceptInvitationView,
    DepartmentViewSet,
    InvitationPreviewView,
    InvitationViewSet,
    MembershipViewSet,
    OrganizationViewSet,
    TeamViewSet,
)

app_name = "organizations"

router = DefaultRouter()
router.register("members", MembershipViewSet, basename="membership")
router.register("departments", DepartmentViewSet, basename="department")
router.register("teams", TeamViewSet, basename="team")
router.register("invitations", InvitationViewSet, basename="invitation")
router.register("", OrganizationViewSet, basename="organization")

urlpatterns = [
    path(
        "invitations/preview/<str:token>/",
        InvitationPreviewView.as_view(),
        name="invitation-preview",
    ),
    path("invitations/accept/", AcceptInvitationView.as_view(), name="invitation-accept"),
    path("", include(router.urls)),
]
