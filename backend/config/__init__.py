"""NexusCRM project configuration package.

Importing the Celery application here guarantees that the shared_task decorator
uses this project's app whenever Django starts.
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
