import datetime

from celery import Celery
from django.conf import settings
from django.db import transaction
from tapir_mail.service.shortcuts import make_timezone_aware

app = Celery("tapir", broker=settings.CELERY_BROKER_URL)


from tapir.wirgarten.models import ScheduledTask


@transaction.atomic
def schedule_task_unique(task, eta: datetime.datetime, args=(), kwargs=None):
    if kwargs is None:
        kwargs = {}

    st_args = {
        "task_function": f"{task.__module__}.{task.__name__}",
        "task_args": args,
        "task_kwargs": kwargs,
    }

    existing = ScheduledTask.objects.filter(**st_args)
    if existing.exists():
        existing.delete()
    print("Deleted duplicate task: ", ", ".join([e for e in existing]))

    if not isinstance(eta, datetime.datetime) and isinstance(eta, datetime.date):
        eta = datetime.datetime.combine(eta, datetime.time())

    scheduled_task = ScheduledTask.objects.create(
        **st_args, eta=make_timezone_aware(eta)
    )
    print("Scheduled new task: ", scheduled_task)
