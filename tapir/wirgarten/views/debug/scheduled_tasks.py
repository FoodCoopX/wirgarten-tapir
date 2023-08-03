from datetime import datetime
from typing import Any, Dict

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import ScheduledTask
from tapir.wirgarten.utils import get_now


class ScheduledTasksListView(
    PermissionRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    permission_required = Permission.Coop.MANAGE
    template_name = "wirgarten/debug/scheduled_tasks.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        time_offset = get_now() + relativedelta(days=-1)

        ctx["tasks"] = [
            {
                "id": t.id,
                "name": t.task_function,
                "eta": t.eta,
                "args": t.task_args,
                "kwargs": t.task_kwargs,
                "status": t.status,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in ScheduledTask.objects.all()
            .filter(eta__gte=time_offset)
            .order_by("eta")
        ]

        return ctx
