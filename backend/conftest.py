"""Project-wide pytest fixtures.

These fixtures give every test suite a ready-made tenant: an organization, an
owner, an admin, a plain member, and authenticated API clients for each.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture()
def api_client() -> APIClient:
    """Unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture()
def password() -> str:
    return "TestPassw0rd!123"


@pytest.fixture()
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(
        name="Acme Corporation",
        slug="acme-corporation",
        industry="technology",
        company_size="51-200",
        country="US",
        timezone="UTC",
        currency="USD",
    )


@pytest.fixture()
def other_organization(db):
    """A second tenant, used to prove isolation between organizations."""
    from apps.organizations.models import Organization

    return Organization.objects.create(
        name="Globex Industries",
        slug="globex-industries",
        industry="manufacturing",
        company_size="201-500",
        country="US",
        timezone="UTC",
        currency="USD",
    )


def _make_member(user, organization, role):
    from apps.organizations.models import OrganizationMembership

    return OrganizationMembership.objects.create(
        organization=organization, user=user, role=role, is_active=True
    )


@pytest.fixture()
def owner_user(db, organization, password):
    user = User.objects.create_user(
        email="owner@acme.test",
        password=password,
        first_name="Olivia",
        last_name="Owner",
        is_email_verified=True,
    )
    _make_member(user, organization, "owner")
    user.active_organization = organization
    user.save(update_fields=["active_organization"])
    return user


@pytest.fixture()
def admin_user(db, organization, password):
    user = User.objects.create_user(
        email="admin@acme.test",
        password=password,
        first_name="Adam",
        last_name="Admin",
        is_email_verified=True,
    )
    _make_member(user, organization, "admin")
    user.active_organization = organization
    user.save(update_fields=["active_organization"])
    return user


@pytest.fixture()
def member_user(db, organization, password):
    user = User.objects.create_user(
        email="member@acme.test",
        password=password,
        first_name="Mia",
        last_name="Member",
        is_email_verified=True,
    )
    _make_member(user, organization, "member")
    user.active_organization = organization
    user.save(update_fields=["active_organization"])
    return user


@pytest.fixture()
def foreign_user(db, other_organization, password):
    """A user belonging to a different tenant."""
    user = User.objects.create_user(
        email="intruder@globex.test",
        password=password,
        first_name="Frank",
        last_name="Foreign",
        is_email_verified=True,
    )
    _make_member(user, other_organization, "owner")
    user.active_organization = other_organization
    user.save(update_fields=["active_organization"])
    return user


def _authenticate(client: APIClient, user) -> APIClient:
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture()
def auth_client(api_client, member_user):
    """API client authenticated as a regular member."""
    return _authenticate(api_client, member_user)


@pytest.fixture()
def admin_client(admin_user):
    return _authenticate(APIClient(), admin_user)


@pytest.fixture()
def owner_client(owner_user):
    return _authenticate(APIClient(), owner_user)


@pytest.fixture()
def foreign_client(foreign_user):
    """Authenticated client from another organization (isolation tests)."""
    return _authenticate(APIClient(), foreign_user)


@pytest.fixture(autouse=True)
def _clear_tenant_context():
    """Ensure thread-local tenant state never leaks between tests."""
    from apps.common.context import clear_current_context

    clear_current_context()
    yield
    clear_current_context()
