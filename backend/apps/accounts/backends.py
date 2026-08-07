"""Authentication backends."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from apps.common.utils import normalise_email

User = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate with an email address instead of a username.

    Runs the password hasher even when no user matches, so that response timing
    does not reveal whether an address is registered.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if not email or not password:
            return None

        email = normalise_email(email)
        user = User.objects.filter(Q(email__iexact=email)).first()

        if user is None:
            User().set_password(password)  # constant-time-ish guard
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user) -> bool:
        return bool(user.is_active and not user.is_deleted)
