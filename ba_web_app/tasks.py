from ba_web_app.celery_utils import celery


@celery.task
def add_numbers(a, b):
    return a + b

