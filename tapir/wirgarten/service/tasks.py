import inspect
import json
from datetime import datetime

from celery import Celery
from tapir import settings

app = Celery("tapir", broker=settings.CELERY_BROKER_URL)


def schedule_task_unique(task, eta: datetime, args=(), kwargs={}):
    """
    Scheduling tasks via this function makes sure that the task is unique by args.
    All other tasks of the same type with the same args/kwargs combination are revoked.
    """

    cinspect = app.control.inspect()
    scheduled_tasks = cinspect.scheduled()
    revoked_tasks = set(
        [item for sublist in cinspect.revoked().values() for item in sublist]
    )

    module = inspect.getmodule(task)
    new_task_serialized = json.dumps(
        {
            "type": f"{module.__name__}.{task.__name__}",
            "args": args,
            "kwargs": kwargs,
        }
    )

    if scheduled_tasks:
        for t in [x for tasks in scheduled_tasks.values() for x in tasks]:
            task_id = t["request"]["id"]
            if task_id not in revoked_tasks:
                serialized = json.dumps(
                    {
                        "type": t["request"]["type"],
                        "args": t["request"]["args"],
                        "kwargs": t["request"]["kwargs"],
                    }
                )

                if serialized == new_task_serialized:
                    app.control.revoke(task_id)
                    print("Revoked duplicate task: ", serialized)

    task.apply_async(args=args, kwargs=kwargs, eta=eta)

    print(f"Task scheduled: {eta} {new_task_serialized}")
