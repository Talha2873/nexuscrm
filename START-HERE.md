# Start here

Everything — backend, frontend, infrastructure — is in this one folder.
Two commands and you're running.

```
nexuscrm/
├── backend/            Django 5 + DRF API
├── frontend/           React 19 + Vite SPA
├── nginx/              Reverse proxy config
├── .github/workflows/  CI
├── docker-compose.yml  Runs everything together
└── .env.example        Copy to .env before starting
```

---

## Option A — Docker (recommended)

Requires Docker 24+ with Compose v2. Nothing else to install.

```bash
cd nexuscrm
cp .env.example .env          # edit SECRET_KEY; everything else has a default
docker compose up --build     # first build takes a few minutes
```

Then, in a second terminal:

```bash
# Migrations are not committed, so generate them once
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Load the demo workspace (6 users, teams, departments, tags)
docker compose exec backend python manage.py seed_data
```

Open **http://localhost:5173** and sign in:

| Email | Password | Role |
|-------|----------|------|
| `demo@nexuscrm.io` | `Demo1234!` | Owner |
| `amara@nexuscrm.io` | `Demo1234!` | Administrator |
| `jonas@nexuscrm.io` | `Demo1234!` | Manager |
| `priya@nexuscrm.io` | `Demo1234!` | Member |
| `sofia@nexuscrm.io` | `Demo1234!` | Viewer |

Sign in as different people to watch the UI change with their role — a Viewer
sees no create buttons, a Member can't reach Invitations, only an Admin can open
the Audit log.

| What | Where |
|------|-------|
| App | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/docs/ |
| Django admin | http://localhost:8000/admin/ |
| Health check | http://localhost:8000/health/ |

---

## Option B — Run the two halves yourself

You'll need Python 3.12, Node 20, PostgreSQL 16 and Redis 7 running locally.

**Terminal 1 — backend**

```bash
cd nexuscrm/backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp ../.env.example .env
# In .env set POSTGRES_HOST=localhost and REDIS_URL=redis://localhost:6379/0

python manage.py makemigrations
python manage.py migrate
python manage.py seed_data
python manage.py runserver 8000
```

**Terminal 2 — frontend**

```bash
cd nexuscrm/frontend
npm install
cp .env.example .env.local
npm run dev
```

Background workers are optional for browsing; emails just won't send. To enable
them, add two more terminals:

```bash
cd backend && celery -A config worker -l info
cd backend && celery -A config beat -l info
```

---

## Verifying it works

```bash
cd backend  && pytest          # backend test suite
cd frontend && npm run test:ci # frontend unit tests
```

Without SMTP configured, verification and invitation emails print to the backend
console instead of sending — look there for the links.

---

## Two things to know

**1. No migrations are committed.** Run `makemigrations` once, as shown above.
This is deliberate: hand-written migrations drift from the models, so it's safer
to let Django generate them against your database.

**2. This is a work in progress.** Auth, multi-tenancy, members, teams,
departments, invitations, search, activity and audit logging are complete and
working. Customers, deals, tasks, tickets, notifications, reports and the AI
assistant are not built yet — see the Build status table in `README.md`.

Apps get registered in `backend/config/settings/base.py` and
`backend/config/api_urls.py` as they're finished, which is why the app boots
cleanly and `/docs/` only lists endpoints that really exist.
