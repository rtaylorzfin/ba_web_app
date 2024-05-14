from ba_web_app.app import create_app
from ba_web_app.celery_utils import init_celery

app = create_app()
celery = init_celery(app)
