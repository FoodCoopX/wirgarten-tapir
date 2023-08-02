from datetime import datetime
from typing import Any, Dict

from celery import Celery
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic

from tapir import settings
from tapir.wirgarten.constants import Permission

app = Celery("tapir", broker=settings.CELERY_BROKER_URL)


class ScheduledTasksListView(
    PermissionRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    permission_required = Permission.Coop.MANAGE
    template_name = "wirgarten/debug/scheduled_tasks.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        celery = app.control.inspect()

        revoked_tasks = set(
            [item for sublist in celery.revoked().values() for item in sublist]
        )

        flat_tasks = []

        scheduled_tasks = celery.scheduled()
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                flat_tasks.extend(
                    [
                        {
                            "worker": worker,
                            "id": x["request"]["id"],
                            "name": x["request"]["name"],
                            "eta": datetime.fromisoformat(x["eta"]),
                            "args": x["request"]["args"],
                            "kwargs": x["request"]["kwargs"],
                            "acknowledged": x["request"]["acknowledged"],
                        }
                        for x in tasks
                        if x["request"]["id"] not in revoked_tasks
                    ]
                )

            ping_status = celery.ping()
            ctx["workers"] = [
                {"id": x, "alive": ping_status[x]} for x in scheduled_tasks.keys()
            ]
            ctx["celery_alive"] = True
        else:
            ctx["celery_alive"] = False

        ctx["tasks"] = flat_tasks
        return ctx
