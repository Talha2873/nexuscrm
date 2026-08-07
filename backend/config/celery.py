"""Celery application for NexusCRM."""
from __future__ import annotations

import logging
import os

from celery import Celery
from celery.signals import setup_logging, task_failure

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("nexuscrm")

# All Celery configuration lives in Django settings under the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover `tasks.py` in every installed app.
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@setup_logging.connect
def configure_logging(**kwargs):  # pragma: no cover - wiring
    """Let Django's LOGGING dict control Celery logging too."""
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


@task_failure.connect
def report_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Log every task failure with enough context to debug it."""
    logger.error(
        "Celery task failed: task=%s id=%s error=%s",
        getattr(sender, "name", "unknown"),
        task_id,
        exception,
        exc_info=kwargs.get("einfo"),
    )


@app.task(bind=True, name="config.debug_task")
def debug_task(self):
    """Trivial task used to verify the worker is alive."""
    return {"request_id": self.request.id, "status": "ok"}
