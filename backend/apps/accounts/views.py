"""Authentication endpoints."""
from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.common.serializers import ErrorResponseSerializer, SuccessResponseSerializer

from .serializers import (
    AuthResponseSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
    OrganizationBriefSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    SocialAccountSerializer,
    SwitchOrganizationSerializer,
    TokenPairSerializer,
    UserSerializer,
    UserSessionSerializer,
    UserUpdateSerializer,
)
from .services import AuthService, ProfileService

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthThrottle(ScopedRateThrottle):
    scope = "auth"


def _auth_payload(result: dict, request) -> dict:
    """Shape the standard authentication response."""
    context = {"request": request}
    return {
        "success": True,
        "user": UserSerializer(result["user"], context=context).data,
        "organization": (
            OrganizationBriefSerializer(result["organization"], context=context).data
            if result.get("organization")
            else None
        ),
        "tokens": result["tokens"],
    }


# ---------------------------------------------------------------------------
# Registration & login
# ---------------------------------------------------------------------------
@extend_schema(tags=["Authentication"])
class RegisterView(APIView):
    """Create an account, provision or join an organization, and return tokens."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Register a new account",
        request=RegisterSerializer,
        responses={201: AuthResponseSerializer, 400: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService().register(request=request, **serializer.validated_data)
        return Response(_auth_payload(result, request), status=status.HTTP_201_CREATED)


@extend_schema(tags=["Authentication"])
class LoginView(APIView):
    """Exchange email + password for a JWT pair."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Log in",
        request=LoginSerializer,
        responses={200: AuthResponseSerializer, 400: ErrorResponseSerializer, 429: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService().login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            request=request,
        )
        return Response(_auth_payload(result, request))


@extend_schema(tags=["Authentication"])
class GoogleLoginView(APIView):
    """Log in (or sign up) with a Google ID token."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Log in with Google",
        request=GoogleLoginSerializer,
        responses={200: AuthResponseSerializer, 400: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService().google_login(
            id_token_str=serializer.validated_data["id_token"], request=request
        )
        payload = _auth_payload(result, request)
        payload["created"] = result.get("created", False)
        return Response(
            payload,
            status=status.HTTP_201_CREATED if result.get("created") else status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class TokenRefreshView(APIView):
    """Exchange a refresh token for a new access token."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        summary="Refresh the access token",
        request=RefreshTokenSerializer,
        responses={200: TokenPairSerializer, 401: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh = RefreshToken(serializer.validated_data["refresh"])
        except TokenError as exc:
            raise InvalidToken("This refresh token is invalid or has expired.") from exc

        from django.conf import settings

        data = {
            "access": str(refresh.access_token),
            "access_expires_in": int(
                settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
            ),
        }
        # Rotation is enabled, so hand back the rotated refresh token too.
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
            if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION"):
                try:
                    refresh.blacklist()
                except AttributeError:  # pragma: no cover - blacklist app disabled
                    pass
            user = User.objects.filter(id=refresh.get("user_id")).first()
            if user is not None:
                new_refresh = RefreshToken.for_user(user)
                data["refresh"] = str(new_refresh)
                data["refresh_expires_in"] = int(
                    settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
                )

        return Response({"success": True, **data})


@extend_schema(tags=["Authentication"])
class TokenVerifyView(APIView):
    """Check whether an access token is still usable."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        summary="Verify an access token",
        request=None,
        responses={200: SuccessResponseSerializer, 401: ErrorResponseSerializer},
    )
    def post(self, request):
        token = request.data.get("token", "")
        try:
            AccessToken(token)
        except TokenError as exc:
            raise InvalidToken("This token is invalid or has expired.") from exc
        return Response({"success": True, "message": "Token is valid."})


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    """Blacklist the refresh token, optionally on every device."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Log out",
        request=LogoutSerializer,
        responses={200: SuccessResponseSerializer},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AuthService()
        if serializer.validated_data.get("all_devices"):
            revoked = service.logout_all(request.user)
            return Response(
                {"success": True, "message": f"Signed out of {revoked} session(s)."}
            )

        refresh = serializer.validated_data.get("refresh")
        if refresh:
            service.logout(refresh, user=request.user)
        return Response({"success": True, "message": "Signed out successfully."})


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
@extend_schema(tags=["Authentication"])
class VerifyEmailView(APIView):
    """Confirm an email address using the token from the verification email."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Verify an email address",
        request=EmailVerificationSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService().verify_email(serializer.validated_data["token"])
        return Response(
            {
                "success": True,
                "message": "Your email address has been verified.",
                "user": UserSerializer(user, context={"request": request}).data,
            }
        )


@extend_schema(tags=["Authentication"])
class ResendVerificationView(APIView):
    """Re-send the verification email. Always reports success."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Resend the verification email",
        request=ResendVerificationSerializer,
        responses={200: SuccessResponseSerializer},
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService().resend_verification(serializer.validated_data["email"], request=request)
        return Response(
            {
                "success": True,
                "message": "If that address needs verification, we've sent a new link.",
            }
        )


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
@extend_schema(tags=["Authentication"])
class ForgotPasswordView(APIView):
    """Start the password reset flow. Never reveals whether an account exists."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Request a password reset link",
        request=ForgotPasswordSerializer,
        responses={200: SuccessResponseSerializer},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService().request_password_reset(
            serializer.validated_data["email"], request=request
        )
        return Response(
            {
                "success": True,
                "message": "If an account exists for that address, a reset link is on its way.",
            }
        )


@extend_schema(tags=["Authentication"])
class ResetPasswordView(APIView):
    """Complete the password reset using the emailed token."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Reset a password with a token",
        request=ResetPasswordSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService().reset_password(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["password"],
            request=request,
        )
        return Response(
            {
                "success": True,
                "message": "Your password has been reset. Please sign in again.",
            }
        )


@extend_schema(tags=["Authentication"])
class ChangePasswordView(APIView):
    """Change the password of the signed-in user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change your password",
        request=ChangePasswordSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        AuthService().change_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
            request=request,
        )
        return Response({"success": True, "message": "Your password has been changed."})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@extend_schema_view(
    get=extend_schema(summary="Get the signed-in user", tags=["Authentication"]),
    patch=extend_schema(summary="Update your profile", tags=["Authentication"]),
    put=extend_schema(summary="Replace your profile", tags=["Authentication"]),
)
class MeView(APIView):
    """Read and update the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(
            {"success": True, "user": UserSerializer(request.user, context={"request": request}).data}
        )

    @extend_schema(request=UserUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = ProfileService().update_profile(request.user, **serializer.validated_data)
        return Response(
            {"success": True, "user": UserSerializer(user, context={"request": request}).data}
        )

    @extend_schema(request=UserUpdateSerializer, responses={200: UserSerializer})
    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = ProfileService().update_profile(request.user, **serializer.validated_data)
        return Response(
            {"success": True, "user": UserSerializer(user, context={"request": request}).data}
        )


@extend_schema(tags=["Authentication"])
class AvatarUploadView(APIView):
    """Upload or remove the signed-in user's avatar."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload an avatar",
        request=AvatarUploadSerializer,
        responses={200: UserSerializer},
    )
    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.avatar = serializer.validated_data["avatar"]
        user.save(update_fields=["avatar", "updated_at"])
        return Response(
            {"success": True, "user": UserSerializer(user, context={"request": request}).data}
        )

    @extend_schema(summary="Remove your avatar", responses={200: SuccessResponseSerializer})
    def delete(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=["avatar", "updated_at"])
        return Response({"success": True, "message": "Avatar removed."})


@extend_schema(tags=["Authentication"])
class SwitchOrganizationView(APIView):
    """Change which organization the user is currently working in."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Switch the active organization",
        request=SwitchOrganizationSerializer,
        responses={200: AuthResponseSerializer, 403: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = SwitchOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = AuthService().switch_organization(
            request.user, serializer.validated_data["organization_id"]
        )
        request.user.refresh_from_db()
        return Response(
            {
                "success": True,
                "user": UserSerializer(request.user, context={"request": request}).data,
                "organization": OrganizationBriefSerializer(
                    organization, context={"request": request}
                ).data,
            }
        )


# ---------------------------------------------------------------------------
# Sessions & linked accounts
# ---------------------------------------------------------------------------
@extend_schema(tags=["Authentication"])
class SessionListView(APIView):
    """List the user's active sessions."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="List active sessions", responses={200: UserSessionSerializer(many=True)})
    def get(self, request):
        sessions = AuthService().list_sessions(request.user)
        serializer = UserSessionSerializer(sessions, many=True, context={"request": request})
        return Response({"success": True, "results": serializer.data})


@extend_schema(tags=["Authentication"])
class SessionDetailView(APIView):
    """Revoke a single session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Revoke a session", responses={200: SuccessResponseSerializer})
    def delete(self, request, session_id):
        AuthService().revoke_session(request.user, session_id)
        return Response({"success": True, "message": "Session revoked."})


@extend_schema(tags=["Authentication"])
class SocialAccountListView(APIView):
    """List identity providers linked to the account."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="List linked social accounts", responses={200: SocialAccountSerializer(many=True)})
    def get(self, request):
        accounts = request.user.social_accounts.all()
        serializer = SocialAccountSerializer(accounts, many=True)
        return Response({"success": True, "results": serializer.data})


@extend_schema(tags=["Authentication"])
class SocialAccountDetailView(APIView):
    """Unlink an identity provider."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Unlink a social account", responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer})
    def delete(self, request, account_id):
        from apps.common.exceptions import BusinessRuleViolation, ResourceNotFound

        account = request.user.social_accounts.filter(id=account_id).first()
        if account is None:
            raise ResourceNotFound("Linked account not found.")
        if not request.user.has_usable_password() and request.user.social_accounts.count() == 1:
            raise BusinessRuleViolation(
                "Set a password before unlinking your only sign-in method."
            )
        account.delete()
        return Response({"success": True, "message": "Account unlinked."})


@extend_schema(tags=["Authentication"])
class DeactivateAccountView(APIView):
    """Deactivate the signed-in user's account."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Deactivate your account", request=None, responses={200: SuccessResponseSerializer})
    def post(self, request):
        ProfileService().deactivate(request.user)
        return Response({"success": True, "message": "Your account has been deactivated."})
