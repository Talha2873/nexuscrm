"""Populate a demo organization so a fresh install is immediately explorable.

    python manage.py seed_data
    python manage.py seed_data --reset      # delete the demo org first

The command is idempotent: running it twice will not duplicate anything.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.common.constants import OrganizationRole
from apps.common.context import tenant_context
from apps.common.models import Note, Tag
from apps.organizations.models import (
    Department,
    Invitation,
    Organization,
    OrganizationMembership,
    Team,
    TeamMembership,
)

User = get_user_model()

DEMO_SLUG = "nexus-demo"
DEMO_PASSWORD = "Demo1234!"

DEMO_PEOPLE = [
    ("demo@nexuscrm.io", "Dana", "Okonkwo", OrganizationRole.OWNER, "Founder & CEO"),
    ("amara@nexuscrm.io", "Amara", "Silva", OrganizationRole.ADMIN, "Head of Operations"),
    ("jonas@nexuscrm.io", "Jonas", "Weber", OrganizationRole.MANAGER, "Sales Manager"),
    ("priya@nexuscrm.io", "Priya", "Raman", OrganizationRole.MEMBER, "Account Executive"),
    ("liam@nexuscrm.io", "Liam", "O'Connell", OrganizationRole.MEMBER, "Support Engineer"),
    ("sofia@nexuscrm.io", "Sofia", "Marchetti", OrganizationRole.VIEWER, "Finance Analyst"),
]

DEPARTMENTS = [
    ("Revenue", "REV", "Everything that touches the customer's wallet.", "#2563eb"),
    ("Operations", "OPS", "Keeps the business running day to day.", "#0891b2"),
    ("Customer Success", "CS", "Onboarding, support and retention.", "#059669"),
]

TEAMS = [
    ("Enterprise Sales", "Revenue", "Deals above $50k ARR.", "#2563eb"),
    ("SMB Sales", "Revenue", "Self-serve and small business.", "#7c3aed"),
    ("Support Desk", "Customer Success", "Front line for inbound tickets.", "#059669"),
]

TAGS = [
    ("High priority", "#dc2626"),
    ("Renewal", "#2563eb"),
    ("Champion", "#7c3aed"),
    ("At risk", "#d97706"),
    ("Referral", "#059669"),
]


class Command(BaseCommand):
    help = "Create a demo organization with users, teams, departments and tags."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hard-delete the existing demo organization before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        organization, created = self._create_organization()
        users = self._create_users(organization)
        departments = self._create_departments(organization)
        self._create_teams(organization, departments, users)
        self._create_tags(organization)
        self._create_invitation(organization, users["demo@nexuscrm.io"])
        self._create_welcome_note(organization, users["demo@nexuscrm.io"])

        verb = "Created" if created else "Refreshed"
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{verb} demo workspace '{organization.name}'"))
        self.stdout.write("")
        self.stdout.write("  Sign in with any of these accounts:")
        self.stdout.write("")
        for email, first, last, role, _title in DEMO_PEOPLE:
            self.stdout.write(f"    {email:<26} {DEMO_PASSWORD}   ({role})")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("  These are demo credentials. Never seed them in production."))
        self.stdout.write("")

    # ------------------------------------------------------------------
    def _reset(self) -> None:
        organization = Organization.all_objects.filter(slug=DEMO_SLUG).first()
        if organization is None:
            return
        User.all_objects.filter(memberships__organization=organization).delete()
        organization.delete(hard=True)
        self.stdout.write(self.style.WARNING("Removed the previous demo workspace."))

    def _create_organization(self) -> tuple[Organization, bool]:
        organization = Organization.all_objects.filter(slug=DEMO_SLUG).first()
        if organization is not None:
            return organization, False

        organization = Organization.objects.create(
            name="Nexus Demo Company",
            slug=DEMO_SLUG,
            legal_name="Nexus Demo Company Ltd.",
            description="A sample workspace showing how NexusCRM fits together.",
            industry="technology",
            company_size="medium",
            website="https://demo.nexuscrm.io",
            email="hello@nexuscrm.io",
            city="Lisbon",
            country="PT",
            timezone="Europe/Lisbon",
            currency="EUR",
            plan=Organization.Plan.PROFESSIONAL,
            max_users=25,
            max_storage_mb=10_240,
            trial_ends_at=timezone.now() + timezone.timedelta(days=21),
            onboarding_completed=True,
        )
        return organization, True

    def _create_users(self, organization: Organization) -> dict[str, User]:
        users: dict[str, User] = {}

        for email, first, last, role, title in DEMO_PEOPLE:
            user = User.all_objects.filter(email__iexact=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=DEMO_PASSWORD,
                    first_name=first,
                    last_name=last,
                    job_title=title,
                    is_email_verified=True,
                    timezone="Europe/Lisbon",
                )
            users[email] = user

            OrganizationMembership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={"role": role, "title": title, "is_active": True},
            )

            if user.active_organization_id is None:
                user.active_organization = organization
                user.save(update_fields=["active_organization"])

        owner = users["demo@nexuscrm.io"]
        if organization.owner_id != owner.id:
            organization.owner = owner
            organization.save(update_fields=["owner"])

        self.stdout.write(f"  · {len(users)} users")
        return users

    def _create_departments(self, organization: Organization) -> dict[str, Department]:
        departments: dict[str, Department] = {}
        with tenant_context(organization=organization):
            for name, code, description, color in DEPARTMENTS:
                department, _ = Department.objects.get_or_create(
                    organization=organization,
                    name=name,
                    defaults={"code": code, "description": description, "color": color},
                )
                departments[name] = department
        self.stdout.write(f"  · {len(departments)} departments")
        return departments

    def _create_teams(self, organization, departments, users) -> None:
        created = 0
        with tenant_context(organization=organization):
            for name, department_name, description, color in TEAMS:
                team, was_created = Team.objects.get_or_create(
                    organization=organization,
                    name=name,
                    defaults={
                        "description": description,
                        "color": color,
                        "department": departments.get(department_name),
                        "lead": users["jonas@nexuscrm.io"],
                    },
                )
                created += int(was_created)

                for email in ("jonas@nexuscrm.io", "priya@nexuscrm.io", "liam@nexuscrm.io"):
                    TeamMembership.objects.get_or_create(
                        team=team,
                        user=users[email],
                        defaults={
                            "organization": organization,
                            "role": "lead" if email == "jonas@nexuscrm.io" else "member",
                        },
                    )
        self.stdout.write(f"  · {len(TEAMS)} teams")

    def _create_tags(self, organization: Organization) -> None:
        with tenant_context(organization=organization):
            for name, color in TAGS:
                Tag.objects.get_or_create(
                    organization=organization, name=name, defaults={"color": color}
                )
        self.stdout.write(f"  · {len(TAGS)} tags")

    def _create_invitation(self, organization: Organization, inviter) -> None:
        with tenant_context(organization=organization, user=inviter):
            Invitation.objects.get_or_create(
                organization=organization,
                email="pending.invitee@example.com",
                status=Invitation.Status.PENDING,
                defaults={
                    "role": OrganizationRole.MEMBER,
                    "message": "We'd love to have you on the team.",
                    "invited_by": inviter,
                },
            )
        self.stdout.write("  · 1 pending invitation")

    def _create_welcome_note(self, organization: Organization, author) -> None:
        org_ct = ContentType.objects.get_for_model(Organization)
        with tenant_context(organization=organization, user=author):
            Note.objects.get_or_create(
                organization=organization,
                author=author,
                content_type=org_ct,
                object_id=organization.id,
                body=(
                    "Welcome to the demo workspace. Explore Members, Teams and "
                    "Departments, then invite a colleague to see the full flow."
                ),
                defaults={"is_pinned": True},
            )
