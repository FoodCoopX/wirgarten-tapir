import os

from celery import Celery
from celery.signals import task_failure

from tapir.utils.services.celery_task_failure_mail_sender import (
    CeleryTaskFailureMailSender,
)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tapir.settings")

app = Celery("tapir")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@task_failure.connect()
def celery_task_failure_email(task_id, exception, sender, einfo, *args, **kwargs):
    CeleryTaskFailureMailSender.on_task_failure(
        task_name=sender.name,
        task_id=task_id,
        exception=exception,
        traceback=str(einfo),
    )
