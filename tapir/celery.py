import os

from celery import Celery
from celery.signals import task_failure
from django.conf import settings
from django.core.mail import mail_admins

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
    subject = f"[celery@{settings.SITE_URL}] Error: Task {sender.name} ({task_id})"
    message = f"""Task {sender.name} with id {task_id} raised exception: {exception!r}
                 Task was called with args: {args} kwargs: {kwargs}.
                 The contents of the full traceback was:
                 {einfo}.
              """.format(**kwargs)
    mail_admins(subject, message)
