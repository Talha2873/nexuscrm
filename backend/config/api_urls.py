"""Version 1 of the NexusCRM REST API.

Every app contributes its own router/urlpatterns; they are mounted here under a
single ``/api/v1/`` prefix so that versioning stays a one-line change.

Routes appear here as their app is implemented, so the schema at ``/docs/``
always reflects endpoints that genuinely exist.
"""
from django.urls import include, path

app_name = "v1"

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("organizations/", include("apps.organizations.urls")),
    # Shared resources (tags, documents, notes, activities, audit logs, search)
    # are mounted last so they occupy the root of /api/v1/ without shadowing
    # the prefixed app routers above.
    path("", include("apps.common.urls")),
]
