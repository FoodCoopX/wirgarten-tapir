from datetime import datetime

from celery import Celery
from django.db import transaction

from django.conf import settings

app = Celery("tapir", broker=settings.CELERY_BROKER_URL)


from tapir.wirgarten.models import ScheduledTask


@transaction.atomic
def schedule_task_unique(task, eta: datetime, args=(), kwargs={}):
    st_args = {
        "task_function": f"{task.__module__}.{task.__name__}",
        "task_args": args,
        "task_kwargs": kwargs,
    }

    existing = ScheduledTask.objects.filter(**st_args)
    if existing.exists():
        existing.delete()
    print("Deleted duplicate task: ", ", ".join([e for e in existing]))

    scheduled_task = ScheduledTask.objects.create(**st_args, eta=eta)
    print("Scheduled new task: ", scheduled_task)
