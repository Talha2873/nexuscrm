"""Pagination classes returning a predictable envelope for the frontend."""
from __future__ import annotations

from collections import OrderedDict

from rest_framework.pagination import (
    CursorPagination,
    LimitOffsetPagination,
    PageNumberPagination,
)
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """Default: ``?page=2&page_size=50``."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("success", True),
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("has_next", self.page.has_next()),
                    ("has_previous", self.page.has_previous()),
                    ("results", data),
                ]
            )
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "count": {"type": "integer", "example": 137},
                "total_pages": {"type": "integer", "example": 6},
                "current_page": {"type": "integer", "example": 1},
                "page_size": {"type": "integer", "example": 25},
                "next": {"type": "string", "nullable": True, "format": "uri"},
                "previous": {"type": "string", "nullable": True, "format": "uri"},
                "has_next": {"type": "boolean"},
                "has_previous": {"type": "boolean"},
                "results": schema,
            },
        }


class LargeResultsSetPagination(StandardResultsSetPagination):
    """For exports and pickers that need bigger pages."""

    page_size = 100
    max_page_size = 1000


class SmallResultsSetPagination(StandardResultsSetPagination):
    """For dense widgets such as dashboard lists."""

    page_size = 10
    max_page_size = 50


class TimelineCursorPagination(CursorPagination):
    """Stable pagination for high-churn feeds (activity timeline, notifications)."""

    page_size = 25
    max_page_size = 100
    page_size_query_param = "page_size"
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("success", True),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class StandardLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 25
    max_limit = 200

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("success", True),
                    ("count", self.count),
                    ("limit", self.limit),
                    ("offset", self.offset),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
