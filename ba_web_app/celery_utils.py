"""
This module contains the Celery configuration for the application.

Use REDIS_URL environment variable to configure Celery (default localhost).
"""

from celery import Celery
from environs import Env

celery = Celery(__name__, include=["ba_web_app.tasks"])

env = Env()
env.read_env()

config_dict = {
    "broker_url": env.str("REDIS_URL", "redis://localhost:6379/0"),
    "result_backend": env.str("REDIS_URL", "redis://localhost:6379/0"),
    "task_ignore_result": False,
}
celery.config_from_object(config_dict)


def init_celery(app):
    """Initialize Celery with Flask application."""
    celery.conf.update(app.config)
    task_base = celery.Task

    class ContextTask(task_base):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return task_base.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
