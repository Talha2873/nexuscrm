"""Global search.

A single query is fanned out across every searchable entity in the tenant, then
merged into a uniform result shape the frontend command palette can render.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from django.db.models import Q


@dataclass(slots=True)
class SearchResult:
    type: str
    id: str
    title: str
    subtitle: str
    url: str
    score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SearchTarget:
    """Declarative description of one searchable entity."""

    key: str
    model_path: str
    fields: tuple[str, ...]
    title_field: str
    subtitle_fields: tuple[str, ...] = ()
    url_template: str = "/{key}/{id}"
    select_related: tuple[str, ...] = ()

    def get_model(self):
        from django.apps import apps as django_apps

        app_label, model_name = self.model_path.split(".")
        return django_apps.get_model(app_label, model_name)


SEARCH_TARGETS: tuple[SearchTarget, ...] = (
    SearchTarget(
        key="customers",
        model_path="customers.Customer",
        fields=("name", "email", "phone", "reference"),
        title_field="name",
        subtitle_fields=("email", "status"),
        url_template="/customers/{id}",
    ),
    SearchTarget(
        key="contacts",
        model_path="contacts.Contact",
        fields=("first_name", "last_name", "email", "phone", "job_title"),
        title_field="full_name",
        subtitle_fields=("email", "job_title"),
        url_template="/contacts/{id}",
        select_related=("company",),
    ),
    SearchTarget(
        key="companies",
        model_path="companies.Company",
        fields=("name", "domain", "email", "phone"),
        title_field="name",
        subtitle_fields=("domain", "industry"),
        url_template="/companies/{id}",
    ),
    SearchTarget(
        key="leads",
        model_path="deals.Lead",
        fields=("first_name", "last_name", "email", "company_name", "phone"),
        title_field="full_name",
        subtitle_fields=("company_name", "status"),
        url_template="/leads/{id}",
    ),
    SearchTarget(
        key="deals",
        model_path="deals.Deal",
        fields=("title", "reference", "description"),
        title_field="title",
        subtitle_fields=("reference", "status"),
        url_template="/deals/{id}",
        select_related=("stage", "customer"),
    ),
    SearchTarget(
        key="projects",
        model_path="tasks.Project",
        fields=("name", "code", "description"),
        title_field="name",
        subtitle_fields=("code", "status"),
        url_template="/projects/{id}",
    ),
    SearchTarget(
        key="tasks",
        model_path="tasks.Task",
        fields=("title", "description"),
        title_field="title",
        subtitle_fields=("status", "priority"),
        url_template="/tasks/{id}",
    ),
    SearchTarget(
        key="tickets",
        model_path="tickets.Ticket",
        fields=("subject", "reference", "description"),
        title_field="subject",
        subtitle_fields=("reference", "status"),
        url_template="/support/{id}",
    ),
    SearchTarget(
        key="invoices",
        model_path="deals.Invoice",
        fields=("number", "notes"),
        title_field="number",
        subtitle_fields=("status", "total_amount"),
        url_template="/invoices/{id}",
    ),
    SearchTarget(
        key="documents",
        model_path="common.Document",
        fields=("name", "description"),
        title_field="name",
        subtitle_fields=("category",),
        url_template="/documents/{id}",
    ),
)


class GlobalSearchService:
    """Fan-out search across all tenant data."""

    def __init__(self, organization, limit_per_type: int = 5) -> None:
        self.organization = organization
        self.limit_per_type = limit_per_type

    def _build_query(self, fields: Iterable[str], term: str) -> Q:
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": term})
        return query

    def _value(self, instance, field: str) -> str:
        value = getattr(instance, field, "")
        if callable(value):
            value = value()
        return "" if value is None else str(value)

    def _score(self, title: str, term: str) -> float:
        """Prefix matches rank above substring matches."""
        title_lower, term_lower = title.lower(), term.lower()
        if title_lower == term_lower:
            return 3.0
        if title_lower.startswith(term_lower):
            return 2.0
        return 1.0

    def search(self, term: str, types: Iterable[str] | None = None) -> list[dict[str, Any]]:
        term = (term or "").strip()
        if len(term) < 2 or self.organization is None:
            return []

        wanted = set(types) if types else None
        results: list[SearchResult] = []

        for target in SEARCH_TARGETS:
            if wanted is not None and target.key not in wanted:
                continue
            try:
                model = target.get_model()
            except LookupError:  # pragma: no cover - app not installed
                continue

            queryset = model.objects.filter(organization=self.organization)
            if target.select_related:
                queryset = queryset.select_related(*target.select_related)
            queryset = queryset.filter(self._build_query(target.fields, term))[
                : self.limit_per_type
            ]

            for instance in queryset:
                title = self._value(instance, target.title_field) or str(instance)
                subtitle = " · ".join(
                    part
                    for part in (
                        self._value(instance, field) for field in target.subtitle_fields
                    )
                    if part
                )
                results.append(
                    SearchResult(
                        type=target.key,
                        id=str(instance.pk),
                        title=title[:255],
                        subtitle=subtitle[:255],
                        url=target.url_template.format(key=target.key, id=instance.pk),
                        score=self._score(title, term),
                    )
                )

        results.sort(key=lambda item: (-item.score, item.type, item.title.lower()))
        return [result.to_dict() for result in results]
