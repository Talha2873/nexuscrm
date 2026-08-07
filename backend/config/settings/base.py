"""
Base Django settings shared by every environment.

Environment-specific modules (development / production / test) import everything
from here and override only what differs.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
# BASE_DIR -> /app (the `backend` directory)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent

env = environ.Env()

# Read .env from the backend dir first, then the repository root.
for candidate in (BASE_DIR / ".env", REPO_DIR / ".env"):
    if candidate.exists():
        environ.Env.read_env(str(candidate))
        break

# ----------------------------------------------------------------------------
# Core
# ----------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="insecure-development-key-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost"])

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----------------------------------------------------------------------------
# Applications
# ----------------------------------------------------------------------------
DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "channels",
    "django_celery_beat",
    "django_celery_results",
]

# Domain apps are registered here as they are implemented. Adding an app is a
# three-line change: append it below, mount its router in `config/api_urls.py`,
# and (if it has consumers) add its routes to `config/routing.py`.
LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.organizations",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ----------------------------------------------------------------------------
# Middleware
# ----------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "apps.common.middleware.CurrentRequestMiddleware",
    "apps.common.middleware.OrganizationMiddleware",
    "apps.common.middleware.AuditLogMiddleware",
]

# ----------------------------------------------------------------------------
# Templates
# ----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ----------------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="nexuscrm"),
        "USER": env("POSTGRES_USER", default="nexuscrm"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="nexuscrm"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {},
    }
}

# ----------------------------------------------------------------------------
# Password validation
# ----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ----------------------------------------------------------------------------
# Internationalisation
# ----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------------------------------
# Static & media
# ----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [d for d in [BASE_DIR / "static"] if d.exists()]

MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=25)
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

ALLOWED_UPLOAD_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".csv", ".txt", ".md", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".zip", ".json",
]

# ----------------------------------------------------------------------------
# Django REST Framework
# ----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.common.authentication.TenantJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "apps.common.authentication.OrganizationHeaderAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="2000/hour"),
        "auth": env("THROTTLE_AUTH", default="20/min"),
        "ai": env("THROTTLE_AI", default="60/hour"),
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    )

# ----------------------------------------------------------------------------
# Simple JWT
# ----------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ----------------------------------------------------------------------------
# drf-spectacular (Swagger / OpenAPI)
# ----------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "NexusCRM API",
    "DESCRIPTION": (
        "AI-powered multi-tenant CRM. Every endpoint is organization-scoped: the "
        "authenticated user's active organization determines which records are "
        "visible. Authenticate with `Bearer <access_token>` obtained from "
        "`/api/v1/auth/login/`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
    },
    "TAGS": [
        {"name": "Authentication", "description": "Login, registration, tokens, password reset"},
        {"name": "Organizations", "description": "Tenants, teams, departments, invitations"},
        {"name": "Users", "description": "User management, roles and permissions"},
        {"name": "Customers", "description": "Customer records and lifecycle"},
        {"name": "Contacts", "description": "People associated with customers and companies"},
        {"name": "Companies", "description": "Company / account records"},
        {"name": "Deals", "description": "Leads, pipelines, deals, invoices and payments"},
        {"name": "Tasks", "description": "Projects, tasks, calendar events"},
        {"name": "Tickets", "description": "Support desk"},
        {"name": "Notifications", "description": "In-app and realtime notifications"},
        {"name": "Reports", "description": "Saved reports and scheduled exports"},
        {"name": "Dashboard", "description": "Aggregated widgets and analytics"},
        {"name": "AI Assistant", "description": "OpenAI/LangChain powered sales assistant"},
        {"name": "Common", "description": "Documents, activities, audit logs, global search"},
    ],
}

# ----------------------------------------------------------------------------
# CORS
# ----------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["X-Request-ID", "X-Total-Count"]
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type", "dnt",
    "origin", "user-agent", "x-csrftoken", "x-requested-with",
    "x-organization-id", "x-request-id",
]

# ----------------------------------------------------------------------------
# Cache (Redis)
# ----------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "nexuscrm",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# ----------------------------------------------------------------------------
# Channels (WebSockets)
# ----------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("CHANNEL_LAYERS_URL", default="redis://localhost:6379/3")],
            "capacity": 1500,
            "expiry": 60,
        },
    }
}

# ----------------------------------------------------------------------------
# Celery
# ----------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_EXTENDED = True
CELERY_BEAT_SCHEDULE = {
    # Housekeeping that ships with the current app set. Domain schedules
    # (analytics snapshots, report dispatch, SLA escalation, lead scoring)
    # are added alongside the apps that own those tasks.
    "database-backup": {
        "task": "apps.common.tasks.database_backup",
        "schedule": crontab(hour=3, minute=0),
    },
    "purge-soft-deleted": {
        "task": "apps.common.tasks.purge_soft_deleted_records",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
    },
    "trim-audit-logs": {
        "task": "apps.common.tasks.trim_audit_logs",
        "schedule": crontab(hour=4, minute=30, day_of_week=0),
    },
    "cleanup-expired-tokens": {
        "task": "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),
    },
    "prune-login-attempts": {
        "task": "apps.accounts.tasks.prune_login_attempts",
        "schedule": crontab(hour=2, minute=30),
    },
    "expire-stale-invitations": {
        "task": "apps.organizations.tasks.expire_stale_invitations",
        "schedule": crontab(hour="*/6", minute=0),
    },
}

CELERY_BEAT_SCHEDULE = {
    "daily-analytics-snapshot": {
        "task": "apps.dashboard.tasks.build_daily_analytics_snapshot",
        "schedule": timedelta(hours=24),
        "options": {"expires": 3600},
    },
    "process-email-queue": {
        "task": "apps.notifications.tasks.process_email_queue",
        "schedule": timedelta(minutes=1),
        "options": {"expires": 55},
    },
    "dispatch-scheduled-reports": {
        "task": "apps.reports.tasks.dispatch_scheduled_reports",
        "schedule": timedelta(minutes=15),
        "options": {"expires": 600},
    },
    "database-backup": {
        "task": "apps.common.tasks.database_backup",
        "schedule": timedelta(hours=24),
        "options": {"expires": 7200},
    },
    "recalculate-lead-scores": {
        "task": "apps.ai_assistant.tasks.recalculate_lead_scores",
        "schedule": timedelta(hours=6),
        "options": {"expires": 3600},
    },
    "escalate-overdue-tickets": {
        "task": "apps.tickets.tasks.escalate_overdue_tickets",
        "schedule": timedelta(minutes=30),
        "options": {"expires": 1500},
    },
    "notify-due-tasks": {
        "task": "apps.tasks.tasks.notify_due_tasks",
        "schedule": timedelta(hours=1),
        "options": {"expires": 3000},
    },
    "purge-expired-notifications": {
        "task": "apps.notifications.tasks.purge_expired_notifications",
        "schedule": timedelta(days=1),
        "options": {"expires": 7200},
    },
}

# ----------------------------------------------------------------------------
# Email
# ----------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="NexusCRM <no-reply@nexuscrm.io>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = env.int("EMAIL_VERIFICATION_TOKEN_TTL_HOURS", default=48)
PASSWORD_RESET_TOKEN_TTL_HOURS = env.int("PASSWORD_RESET_TOKEN_TTL_HOURS", default=2)
INVITATION_TTL_DAYS = env.int("INVITATION_TTL_DAYS", default=14)

# ----------------------------------------------------------------------------
# Google OAuth
# ----------------------------------------------------------------------------
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")

# ----------------------------------------------------------------------------
# OpenAI / LangChain
# ----------------------------------------------------------------------------
AI_ENABLED = env.bool("AI_ENABLED", default=True)
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = env("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")
OPENAI_MAX_TOKENS = env.int("OPENAI_MAX_TOKENS", default=1200)
OPENAI_TEMPERATURE = env.float("OPENAI_TEMPERATURE", default=0.3)
OPENAI_TIMEOUT_SECONDS = env.int("OPENAI_TIMEOUT_SECONDS", default=60)

# ----------------------------------------------------------------------------
# Backups
# ----------------------------------------------------------------------------
BACKUP_DIR = env("BACKUP_DIR", default=str(BASE_DIR / "backups"))
BACKUP_RETENTION_DAYS = env.int("BACKUP_RETENTION_DAYS", default=14)

# ----------------------------------------------------------------------------
# Security defaults (tightened in production.py)
# ----------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {process:d} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": LOG_LEVEL,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "nexuscrm.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "celery": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
    },
}
