"""Authentication routes, mounted at /api/v1/auth/."""
from django.urls import path

from .views import (
    AvatarUploadView,
    ChangePasswordView,
    DeactivateAccountView,
    ForgotPasswordView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    SessionDetailView,
    SessionListView,
    SocialAccountDetailView,
    SocialAccountListView,
    SwitchOrganizationView,
    TokenRefreshView,
    TokenVerifyView,
    VerifyEmailView,
)

app_name = "accounts"

urlpatterns = [
    # ---- Registration & login ----
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # ---- Tokens ----
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # ---- Email verification ----
    path("email/verify/", VerifyEmailView.as_view(), name="verify-email"),
    path("email/resend/", ResendVerificationView.as_view(), name="resend-verification"),
    # ---- Passwords ----
    path("password/forgot/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("password/reset/", ResetPasswordView.as_view(), name="reset-password"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
    # ---- Profile ----
    path("me/", MeView.as_view(), name="me"),
    path("me/avatar/", AvatarUploadView.as_view(), name="avatar"),
    path("me/deactivate/", DeactivateAccountView.as_view(), name="deactivate"),
    path("me/switch-organization/", SwitchOrganizationView.as_view(), name="switch-organization"),
    # ---- Sessions ----
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/<uuid:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    # ---- Linked accounts ----
    path("social-accounts/", SocialAccountListView.as_view(), name="social-account-list"),
    path(
        "social-accounts/<uuid:account_id>/",
        SocialAccountDetailView.as_view(),
        name="social-account-detail",
    ),
]
