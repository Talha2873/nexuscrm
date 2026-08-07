"""FilterSets for the organizations app."""
from django_filters import rest_framework as filters

from apps.common.filters import BaseFilterSet

from .models import Department, Invitation, OrganizationMembership, Team


class MembershipFilter(BaseFilterSet):
    role = filters.MultipleChoiceFilter(
        choices=OrganizationMembership._meta.get_field("role").choices
    )
    is_active = filters.BooleanFilter()
    department = filters.UUIDFilter(field_name="department_id")
    email = filters.CharFilter(field_name="user__email", lookup_expr="icontains")
    name = filters.CharFilter(method="filter_name")

    class Meta:
        model = OrganizationMembership
        fields = ["role", "is_active", "department"]

    def filter_name(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(
            Q(user__first_name__icontains=value) | Q(user__last_name__icontains=value)
        )


class TeamFilter(BaseFilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    department = filters.UUIDFilter(field_name="department_id")
    lead = filters.UUIDFilter(field_name="lead_id")
    is_active = filters.BooleanFilter()
    member = filters.UUIDFilter(method="filter_member")

    class Meta:
        model = Team
        fields = ["name", "department", "lead", "is_active"]

    def filter_member(self, queryset, name, value):
        return queryset.filter(
            team_memberships__user_id=value, team_memberships__is_active=True
        ).distinct()


class DepartmentFilter(BaseFilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    parent = filters.UUIDFilter(field_name="parent_id")
    head = filters.UUIDFilter(field_name="head_id")
    top_level = filters.BooleanFilter(field_name="parent", lookup_expr="isnull")

    class Meta:
        model = Department
        fields = ["name", "parent", "head"]


class InvitationFilter(BaseFilterSet):
    status = filters.MultipleChoiceFilter(
        choices=Invitation._meta.get_field("status").choices
    )
    role = filters.CharFilter()
    email = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Invitation
        fields = ["status", "role", "email"]
