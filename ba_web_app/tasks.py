"""Tasks for Celery to execute asynchronously."""

from ba_web_app.celery_utils import celery


@celery.task
def add_numbers(a, b):
    """Add two numbers."""
    return a + b
