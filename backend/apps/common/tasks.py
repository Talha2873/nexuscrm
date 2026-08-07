"""Maintenance Celery tasks owned by the common app."""
from __future__ import annotations

import logging
import os
import subprocess
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.common.tasks.database_backup", bind=True, max_retries=2)
def database_backup(self) -> dict:
    """Dump PostgreSQL to a gzipped file and prune old dumps."""
    backup_dir = getattr(settings, "BACKUP_DIR", "/app/backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    outfile = os.path.join(backup_dir, f"nexuscrm_{timestamp}.sql.gz")
    db = settings.DATABASES["default"]

    env = {**os.environ, "PGPASSWORD": db["PASSWORD"]}
    command = (
        f'pg_dump -h {db["HOST"]} -p {db["PORT"]} -U {db["USER"]} -d {db["NAME"]} '
        f"--no-owner --no-privileges | gzip -9 > {outfile}"
    )

    try:
        subprocess.run(
            command, shell=True, check=True, env=env, capture_output=True, timeout=1800
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - infra
        logger.error("Database backup failed: %s", exc.stderr)
        raise self.retry(exc=exc, countdown=300) from exc
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - infra
        logger.error("Database backup timed out")
        raise self.retry(exc=exc, countdown=300) from exc

    removed = prune_old_backups(backup_dir)
    size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
    logger.info("Database backup written to %s (%s bytes)", outfile, size)
    return {"file": outfile, "size": size, "pruned": removed}


def prune_old_backups(backup_dir: str) -> int:
    """Delete dumps older than ``settings.BACKUP_RETENTION_DAYS``."""
    retention_days = getattr(settings, "BACKUP_RETENTION_DAYS", 14)
    cutoff = timezone.now() - timedelta(days=retention_days)
    removed = 0
    if not os.path.isdir(backup_dir):
        return 0
    for filename in os.listdir(backup_dir):
        if not filename.startswith("nexuscrm_") or not filename.endswith(".sql.gz"):
            continue
        path = os.path.join(backup_dir, filename)
        modified = timezone.datetime.fromtimestamp(
            os.path.getmtime(path), tz=timezone.get_current_timezone()
        )
        if modified < cutoff:
            os.remove(path)
            removed += 1
    return removed


@shared_task(name="apps.common.tasks.purge_soft_deleted_records")
def purge_soft_deleted_records(days: int = 90) -> dict:
    """Permanently remove records soft-deleted more than ``days`` ago."""
    from django.apps import apps as django_apps

    cutoff = timezone.now() - timedelta(days=days)
    purged: dict[str, int] = {}

    for model in django_apps.get_models():
        if not hasattr(model, "all_objects") or not hasattr(model, "is_deleted"):
            continue
        queryset = model.all_objects.filter(is_deleted=True, deleted_at__lt=cutoff)
        count = queryset.count()
        if count:
            queryset.hard_delete()
            purged[model._meta.label] = count

    logger.info("Purged soft-deleted records: %s", purged)
    return purged


@shared_task(name="apps.common.tasks.trim_audit_logs")
def trim_audit_logs(days: int = 365) -> int:
    """Drop audit entries beyond the retention window."""
    from .models import AuditLog

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = AuditLog.all_objects.filter(created_at__lt=cutoff).delete()
    logger.info("Trimmed %s audit log entries older than %s days", deleted, days)
    return deleted


@shared_task(name="apps.common.tasks.record_activity")
def record_activity(
    organization_id: str,
    actor_id: str | None,
    verb: str,
    description: str,
    app_label: str | None = None,
    model_name: str | None = None,
    object_id: str | None = None,
    metadata: dict | None = None,
) -> str | None:
    """Write a timeline entry asynchronously (used by hot write paths)."""
    from django.contrib.contenttypes.models import ContentType

    from .models import Activity

    content_type = None
    if app_label and model_name:
        content_type = ContentType.objects.filter(
            app_label=app_label, model=model_name
        ).first()

    activity = Activity.objects.create(
        organization_id=organization_id,
        actor_id=actor_id,
        verb=verb,
        description=description[:512],
        metadata=metadata or {},
        content_type=content_type,
        object_id=object_id,
    )
    return str(activity.id)
