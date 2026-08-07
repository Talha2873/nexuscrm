"""Test settings: in-memory where possible, no external services required."""
from .base import *  # noqa: F401,F403
from .base import env  # noqa: F401

DEBUG = False
TESTING = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="nexuscrm_test"),
        "USER": env("POSTGRES_USER", default="nexuscrm"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="nexuscrm"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "ATOMIC_REQUESTS": False,
        "TEST": {"NAME": "nexuscrm_test"},
    }
}

# Fast, deterministic password hashing.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Local memory cache: no Redis dependency in unit tests.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nexuscrm-test",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# In-memory channel layer.
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Celery runs synchronously.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Emails captured by django.core.mail.outbox.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Never hit the OpenAI API from tests.
AI_ENABLED = False
OPENAI_API_KEY = "test-key-not-used"

# Disable throttling.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": (), "DEFAULT_THROTTLE_RATES": {}}  # noqa: F405

MEDIA_ROOT = "/tmp/nexuscrm-test-media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

import logging  # noqa: E402

logging.disable(logging.CRITICAL)
