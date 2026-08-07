"""Development settings: verbose, permissive, fast feedback."""
from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, env  # noqa: F401

DEBUG = True

ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = ["127.0.0.1", "localhost"]

CORS_ALLOW_ALL_ORIGINS = True

# Emails go to the console unless an SMTP backend is explicitly configured.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# Run Celery tasks eagerly when no broker is available locally.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True

# Never enforce HTTPS locally.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Static files served uncompressed for faster reloads.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Generous throttles while developing.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": "1000/min",
    "user": "100000/hour",
    "auth": "1000/min",
    "ai": "1000/hour",
}
