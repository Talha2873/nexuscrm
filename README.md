# NexusCRM — AI-Powered Multi-Tenant CRM

A production-grade CRM built with **Django 5 / DRF** on the backend and **React 19 / Vite** on
the frontend, wired for multi-tenancy, real-time updates, background processing and an
OpenAI-powered sales assistant.

---

## Build status

This repository is being built incrementally. **Everything listed below is
implemented, wired end to end, and runs.** Domain apps are added to
`INSTALLED_APPS`, `config/api_urls.py` and the sidebar as they are completed, so
the app always boots and `/docs/` only ever lists endpoints that genuinely exist.

**Working today**

| Area | What you can do |
|------|-----------------|
| Auth | Register, sign in, sign out, Google sign-in, verify email, forgot/reset password, change password, refresh tokens, view and revoke sessions |
| Tenancy | Create workspaces, switch between them, invite by email, accept/revoke/resend invitations, transfer ownership |
| People | List and search members, change roles, remove and reactivate members |
| Structure | Create and delete teams and departments, add and remove team members |
| Platform | Global search, activity timeline, audit log, tags, notes, document upload, dark mode, responsive layout |

**Not yet built:** customers, contacts, companies, leads/deals/pipeline,
invoices, projects/tasks/calendar, support tickets, notifications and
WebSockets, reports, analytics dashboard, and the AI assistant.

---

## Table of contents

- [Feature overview](#feature-overview)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quick start (Docker)](#quick-start-docker)
- [Manual setup](#manual-setup)
- [Environment variables](#environment-variables)
- [API documentation](#api-documentation)
- [Multi-tenancy model](#multi-tenancy-model)
- [Roles and permissions](#roles-and-permissions)
- [Background jobs](#background-jobs)
- [WebSockets](#websockets)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Feature overview

**Sales & CRM**
Customers, contacts, companies, leads with AI scoring, a configurable sales pipeline, deals,
invoices and payments, projects, tasks, a calendar, and a support desk with SLA tracking.

**AI assistant**
Chat assistant grounded in the tenant's own CRM data, email generator, lead scoring, meeting
summarisation and proposal generation — all through OpenAI + LangChain, with per-tenant
enable/disable switches and usage accounting.

**Platform**
JWT authentication with refresh-token rotation, Google sign-in, email verification, password
reset, granular role-based access control, per-record activity timelines, immutable audit
logs, document uploads, global search, saved reports, scheduled report delivery, analytics
dashboards, and real-time in-app notifications over WebSockets.

---

## Architecture

The backend follows a layered (clean) architecture. Each layer only knows about the one below
it, which keeps business rules testable and makes tenant scoping impossible to forget:

```
HTTP request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ViewSet / APIView          apps/<app>/views.py             │
│  · request validation, permissions, pagination, filtering   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Serializer                 apps/<app>/serializers.py       │
│  · input validation, output shaping                         │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Service                    apps/<app>/services.py          │
│  · business rules, transactions, activity + notifications   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Repository                 apps/<app>/repositories.py      │
│  · the ONLY layer that touches the ORM; always tenant-scoped│
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Model                      apps/<app>/models.py            │
│  · schema, invariants, soft delete, audit columns           │
└─────────────────────────────────────────────────────────────┘
```

Cross-cutting concerns live in `apps/common`: base models, the tenant context, the repository
and service base classes, permissions, pagination, the unified error envelope, middleware,
global search and shared background tasks.

### Backend apps

| App             | Responsibility                                                      |
|-----------------|---------------------------------------------------------------------|
| `common`        | Base models, tenancy, repositories, services, audit, docs, search    |
| `accounts`      | User model, JWT, registration, verification, password reset, OAuth   |
| `organizations` | Tenants, memberships, teams, departments, invitations, settings      |
| `users`         | Profiles, roles, capabilities, preferences                           |
| `customers`     | Customer records and lifecycle                                       |
| `contacts`      | People attached to customers and companies                           |
| `companies`     | Company / account records                                            |
| `deals`         | Leads, pipelines, stages, deals, invoices, payments                  |
| `tasks`         | Projects, tasks, subtasks, calendar events                           |
| `tickets`       | Support desk, SLA, replies                                           |
| `notifications` | In-app + email notifications, WebSocket consumers, email queue       |
| `reports`       | Saved reports, exports, scheduled delivery                           |
| `dashboard`     | Aggregated widgets, analytics snapshots                              |
| `ai_assistant`  | OpenAI/LangChain chat, generators, lead scoring                      |

---

## Tech stack

**Backend** — Python 3.12, Django 5.0, Django REST Framework, PostgreSQL 16, Redis 7,
Celery 5, Django Channels 4 (Daphne), SimpleJWT, drf-spectacular, OpenAI, LangChain,
Gunicorn + Uvicorn workers, Nginx.

**Frontend** — React 19, Vite, React Router, Redux Toolkit, TanStack Query, Axios,
Material UI, Tailwind CSS, React Hook Form, Chart.js.

**Tooling** — Docker & docker-compose, GitHub Actions, pytest, Vitest, ruff, black, ESLint.

---

## Quick start (Docker)

Requirements: Docker 24+ and Docker Compose v2.

```bash
git clone <your-repo-url> nexuscrm
cd nexuscrm

# 1. Configure
cp .env.example .env
#    Edit .env: set SECRET_KEY, and OPENAI_API_KEY if you want the AI features.

# 2. Build and start everything
docker compose up --build

# 3. Generate and apply migrations (first run only — none are committed yet)
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# 4. Create an admin user
docker compose exec backend python manage.py createsuperuser

# 5. (Optional) Load a populated demo workspace
docker compose exec backend python manage.py seed_data
```

| Service          | URL                              |
|------------------|----------------------------------|
| Frontend (Vite)  | http://localhost:5173            |
| Full stack (Nginx) | http://localhost                |
| REST API         | http://localhost:8000/api/v1/    |
| Swagger UI       | http://localhost:8000/docs/      |
| ReDoc            | http://localhost:8000/redoc/     |
| Django admin     | http://localhost:8000/admin/     |
| Health probe     | http://localhost:8000/health/    |

`seed_data` creates a demo workspace with six users. Sign in with any of them
using the password `Demo1234!`:

| Email | Role |
|-------|------|
| `demo@nexuscrm.io` | Owner |
| `amara@nexuscrm.io` | Administrator |
| `jonas@nexuscrm.io` | Manager |
| `priya@nexuscrm.io` | Member |
| `sofia@nexuscrm.io` | Viewer |

Sign in as each to see how role-based access changes the UI. Run
`seed_data --reset` to start over.

---

## Manual setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp ../.env.example .env
# Point POSTGRES_HOST/REDIS_URL at localhost, then:

python manage.py makemigrations   # first run only
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data        # optional demo data
python manage.py runserver          # HTTP only
# or, to serve WebSockets too:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Run the workers in separate terminals:

```bash
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Environment variables

Every variable is documented in [`.env.example`](.env.example). The ones you must set for a
real deployment:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django cryptographic signing key. Use 50+ random characters. |
| `DEBUG` | Must be `False` in production. |
| `ALLOWED_HOSTS` | Comma-separated hostnames the API will answer for. |
| `POSTGRES_*` | Database connection details. |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CHANNEL_LAYERS_URL` | Redis databases for cache, queue and WebSocket groups. |
| `OPENAI_API_KEY` | Required for the AI assistant. Set `AI_ENABLED=False` to disable it. |
| `GOOGLE_OAUTH_CLIENT_ID` | Required for Google sign-in. |
| `EMAIL_*` | SMTP configuration. Defaults to the console backend in development. |
| `FRONTEND_URL` | Used to build links in verification and invitation emails. |

---

## API documentation

The OpenAPI 3 schema is generated from the code, so it never drifts:

- **Swagger UI** — `/docs/` (interactive; click *Authorize* and paste `Bearer <access_token>`)
- **ReDoc** — `/redoc/`
- **Raw schema** — `/schema/`

Every endpoint lives under `/api/v1/`. Adding a `v2` is a one-line change in
`config/urls.py`.

### Response envelope

Successes return the resource directly (or a paginated envelope for lists). Errors always
return the same shape, so the frontend needs one error handler:

```jsonc
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Enter a valid email address.",
    "details": { "email": ["Enter a valid email address."] }
  },
  "request_id": "9f2c1e7a4b..."
}
```

Paginated lists:

```jsonc
{
  "success": true,
  "count": 137,
  "total_pages": 6,
  "current_page": 1,
  "page_size": 25,
  "next": "http://localhost:8000/api/v1/customers/?page=2",
  "previous": null,
  "has_next": true,
  "has_previous": false,
  "results": [ /* ... */ ]
}
```

### Common query parameters

| Parameter | Example | Effect |
|-----------|---------|--------|
| `page`, `page_size` | `?page=2&page_size=50` | Pagination |
| `search` | `?search=acme` | Full-text search over the endpoint's search fields |
| `ordering` | `?ordering=-created_at` | Sort; prefix with `-` for descending |
| `fields` | `?fields=id,name,email` | Sparse fieldsets |
| `created_after`, `created_before` | `?created_after=2026-01-01` | Date filtering |

---

## Multi-tenancy model

NexusCRM uses a **shared database with a tenant discriminator**. Every business model inherits
`TenantBaseModel`, which carries a mandatory `organization` foreign key.

The active tenant is resolved per request, in this order:

1. The `X-Organization-Id` header (lets the UI switch workspaces without re-authenticating).
2. The user's `active_organization`.
3. The user's oldest active membership.

Resolution happens in `apps/common/middleware.OrganizationMiddleware` and again in
`apps/common/authentication.resolve_organization` once DRF has authenticated the token. The
result is published to a thread-local context (`apps/common/context.py`), which means:

- Repositories filter by tenant automatically — you cannot accidentally query across tenants.
- `OrganizationScopedBackend` re-applies the filter as a second line of defence.
- `IsOrganizationMember.has_object_permission` rejects cross-tenant object access.

For Celery tasks and management commands, which have no request, wrap your work in the
explicit context manager:

```python
from apps.common.context import tenant_context

with tenant_context(organization=org, user=system_user):
    DealService().create(title="Renewal", value=5000)
```

---

## Roles and permissions

Five roles, ordered by privilege:

| Role | Can do |
|------|--------|
| `owner` | Everything, including billing and ownership transfer. Exactly one per organization. |
| `admin` | Manage members, teams, settings and all records. |
| `manager` | Manage teams, invite members, edit any record in scope. |
| `member` | Create and edit records; edit only their own where ownership applies. |
| `viewer` | Read-only. |

On top of the hierarchy, `apps/users` supports fine-grained **capabilities** such as
`deals.delete` or `reports.export`, with `deals.*` wildcards. A view opts in by declaring
`required_capability`, enforced by `apps.common.permissions.HasCapability`.

---

## Background jobs

Celery Beat schedules are declared in `config/settings/base.py`:

| Task | Cadence | Purpose |
|------|---------|---------|
| `dashboard.build_daily_analytics_snapshot` | Daily | Pre-aggregate dashboard metrics |
| `notifications.process_email_queue` | Every minute | Drain the outbound email queue |
| `reports.dispatch_scheduled_reports` | Every 15 min | Deliver scheduled reports |
| `common.database_backup` | Daily | `pg_dump` + gzip + retention pruning |
| `ai_assistant.recalculate_lead_scores` | Every 6 hours | Refresh AI lead scores |
| `tickets.escalate_overdue_tickets` | Every 30 min | SLA escalation |
| `tasks.notify_due_tasks` | Hourly | Due-date reminders |

Queues are routed by app: `notifications`, `ai`, `reports`, and the default queue.

---

## WebSockets

Browsers cannot set headers on a WebSocket handshake, so the JWT travels as a query parameter:

```js
const socket = new WebSocket(
  `${WS_BASE_URL}/notifications/?token=${accessToken}&organization=${organizationId}`
);
```

`apps/common/channels_auth.JWTAuthMiddleware` validates the token and populates
`scope["user"]`, `scope["organization"]` and `scope["membership"]`, so consumers enforce the
same tenant boundary as HTTP endpoints.

---

## Testing

```bash
cd backend
pytest                                  # everything
pytest -m api                           # only end-to-end API tests
pytest apps/accounts                    # one app
pytest --cov=apps --cov-report=html     # coverage report in htmlcov/
```

```bash
cd frontend
npm run test          # watch mode
npm run test:ci       # single run, used by CI
```

Shared fixtures live in `backend/conftest.py` and give every test a ready-made tenant: an
organization, an owner, an admin, a member, plus a **second organization with its own user**
so isolation can be asserted directly.

---

## Project layout

```
nexuscrm/
├── backend/
│   ├── config/                 # settings, urls, asgi/wsgi, celery, routing
│   │   └── settings/           # base · development · production · test
│   ├── apps/
│   │   ├── common/             # base models, tenancy, repos, services, audit
│   │   ├── accounts/           # user model + auth flows
│   │   ├── organizations/      # tenants, teams, departments, invitations
│   │   └── ...                 # one package per domain
│   ├── templates/emails/       # transactional email templates
│   ├── scripts/                # entrypoint and backup helpers
│   ├── conftest.py             # shared pytest fixtures
│   └── requirements*.txt
├── frontend/
│   └── src/
│       ├── api/                # axios client + per-domain endpoints
│       ├── components/         # reusable UI
│       ├── features/           # redux slices
│       ├── hooks/              # custom hooks
│       ├── pages/              # routed pages
│       └── store/              # redux store
├── nginx/
├── .github/workflows/
├── docker-compose.yml
└── .env.example
```

---

## Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full guide. The short version:

1. Set `DJANGO_SETTINGS_MODULE=config.settings.production` and a strong `SECRET_KEY`.
2. Set `DEBUG=False` and list your real hostnames in `ALLOWED_HOSTS`.
3. Terminate TLS at Nginx or your load balancer; `SECURE_SSL_REDIRECT` is on by default.
4. Run `python manage.py migrate && python manage.py collectstatic --noinput`.
5. Serve with `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker`.
6. Run at least one Celery worker and exactly one Beat scheduler.
7. Point `SENTRY_DSN` at your project for error tracking.

Verify a deployment with `python manage.py check --deploy`.

---

## Troubleshooting

**`OrganizationRequired` / empty list responses**
The request has no active organization. Ensure the user has an active membership, or send an
`X-Organization-Id` header naming an organization they belong to.

**WebSocket closes immediately**
The token is missing, expired or belongs to a different tenant. Check the browser console for
the close code and confirm `CHANNEL_LAYERS_URL` points at a reachable Redis instance.

**Celery tasks never run**
Confirm the worker is connected to the same `CELERY_BROKER_URL` as the API. In development you
can set `CELERY_TASK_ALWAYS_EAGER=True` to run tasks inline.

**`relation "..." does not exist`**
Migrations have not been applied: `python manage.py migrate`.

---

## Licence

MIT.
