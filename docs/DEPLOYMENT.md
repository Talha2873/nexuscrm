# Deployment guide

This covers taking NexusCRM from a local checkout to a production deployment.
It assumes Docker on a Linux host; adapt paths if you deploy differently.

---

## 1. Prerequisites

- A host with Docker 24+ and Compose v2 (2 vCPU / 4 GB RAM is a sensible floor)
- A domain name pointing at the host
- PostgreSQL 16 and Redis 7 — either the containers in `docker-compose.yml` or
  managed services (recommended for production)
- SMTP credentials for transactional email
- TLS certificates (Let's Encrypt via Certbot works well)

---

## 2. Configure the environment

```bash
cp .env.example .env
```

Set these before anything else:

| Variable | Value |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
| `SECRET_KEY` | 50+ random characters — generate, never reuse |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `crm.example.com,www.crm.example.com` |
| `CORS_ALLOWED_ORIGINS` | `https://crm.example.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://crm.example.com` |
| `POSTGRES_*` | Your database credentials |
| `REDIS_URL` | Cache, broker and channel layer |
| `FRONTEND_URL` | `https://crm.example.com` — used in email links |
| `EMAIL_*` | SMTP host, port, user, password |
| `SENTRY_DSN` | Optional, but do set it |

Generate a key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Never commit `.env`. It is already in `.gitignore`.

---

## 3. Build and start

```bash
docker compose build
docker compose up -d db redis
docker compose run --rm backend python manage.py makemigrations
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py collectstatic --noinput
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d
```

Do **not** run `seed_data` in production — it creates accounts with a known
password.

---

## 4. Verify

```bash
docker compose run --rm backend python manage.py check --deploy
curl -f https://crm.example.com/health/
curl -f https://crm.example.com/ready/
```

`check --deploy` should report no issues. `/ready/` confirms the database and
cache are both reachable; wire it to your load balancer's health check.

---

## 5. TLS

Terminate TLS at Nginx or your load balancer. The production settings already
enable `SECURE_SSL_REDIRECT`, HSTS, secure cookies and
`SECURE_PROXY_SSL_HEADER`, so your proxy must set `X-Forwarded-Proto`.

With Certbot:

```bash
sudo certbot certonly --standalone -d crm.example.com
```

Then mount the certificates into the nginx container and add a `listen 443 ssl`
server block redirecting port 80 to 443.

---

## 6. Background workers

Celery is not optional in production — email delivery, scheduled reports and
backups all depend on it.

- Run **one or more** workers (`celery_worker` service)
- Run **exactly one** beat scheduler (`celery_beat` service). Two schedulers
  means every periodic task fires twice.

```bash
docker compose logs -f celery_worker celery_beat
```

---

## 7. Backups

`apps.common.tasks.database_backup` runs nightly at 03:00 and writes gzipped
dumps to `BACKUP_DIR`, pruning anything older than `BACKUP_RETENTION_DAYS`.

The `backup_data` volume is local to the host, so **copy dumps off the machine**:

```bash
docker compose exec backend ls -lh /app/backups
aws s3 sync ./backups s3://your-bucket/nexuscrm-backups/
```

Test a restore before you need one:

```bash
gunzip -c nexuscrm_20260807_030000.sql.gz | psql -h host -U user -d dbname
```

---

## 8. Scaling

- **Web:** add replicas of the `backend` service behind the load balancer. It is
  stateless apart from Redis and Postgres.
- **WebSockets:** requires sticky sessions or a shared channel layer. The Redis
  channel layer already handles the latter.
- **Workers:** scale by queue. Routes are defined in `CELERY_TASK_ROUTES`
  (`notifications`, `ai`, `reports`, `default`).
- **Static and media:** set `USE_S3=True` plus the `AWS_*` variables to serve
  from S3/CloudFront instead of the local volume.

---

## 9. Upgrading

```bash
git pull
docker compose build
docker compose run --rm backend python manage.py migrate
docker compose up -d
```

Run `migrate` before restarting the web containers so that new code never meets
an old schema.

---

## 10. Monitoring

- **Errors:** Sentry, via `SENTRY_DSN`
- **Health:** `/health/` for liveness, `/ready/` for readiness
- **Queues:** Flower is included in `requirements.txt` —
  `celery -A config flower --port=5555`
- **Logs:** `docker compose logs -f backend`. Every response carries an
  `X-Request-ID` header that also appears in log lines and audit records, so you
  can trace a single request end to end.

---

## Production checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` is unique and secret
- [ ] `ALLOWED_HOSTS` lists only your real domains
- [ ] TLS enabled and HTTP redirects to HTTPS
- [ ] Database credentials are not the defaults
- [ ] `manage.py check --deploy` reports no issues
- [ ] Celery worker and exactly one beat scheduler running
- [ ] Backups running *and* a restore has been tested
- [ ] Sentry receiving events
- [ ] `seed_data` has **not** been run
