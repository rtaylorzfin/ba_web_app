from environs import Env
from celery import Celery
celery = Celery(__name__, include=['ba_web_app.tasks'])

env = Env()
env.read_env()

config_dict = {
    "broker_url": env.str("REDIS_URL"),
    "result_backend": env.str("REDIS_URL"),
    "task_ignore_result": False,
}
celery.config_from_object(config_dict)

def init_celery(app):
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask


# def celery_init_app(app: Flask) -> Celery:
#     class FlaskTask(Task):
#         def __call__(self, *args: object, **kwargs: object) -> object:
#             with app.app_context():
#                 return self.run(*args, **kwargs)
#
#     celery_app = Celery(app.name, task_cls=FlaskTask)
#     celery_app.config_from_object(app.config["CELERY"])
#     celery_app.set_default()
#     app.extensions["celery"] = celery_app
#     return celery_app