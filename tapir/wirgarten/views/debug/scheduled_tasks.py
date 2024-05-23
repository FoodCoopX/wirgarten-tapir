import importlib
import json
import sys
import traceback
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Dict

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

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


class JobsListView(
    PermissionRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    permission_required = Permission.Coop.MANAGE
    template_name = "wirgarten/debug/jobs.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        scheduled = []
        for key, value in settings.CELERY_BEAT_SCHEDULE.items():
            schedule = value["schedule"]
            cron_expression = (
                f"{schedule._orig_minute} {schedule._orig_hour} {schedule._orig_day_of_month} {schedule._orig_month_of_year} {schedule._orig_day_of_week}"
                if hasattr(schedule, "_orig_minute")
                else str(schedule)
            )  # FIXME: proper display of non-cron schedule objects

            scheduled.append(
                {"name": key, "task": value["task"], "schedule": cron_expression}
            )
        ctx["jobs"] = scheduled

        return ctx


@require_POST
@csrf_protect
@permission_required(Permission.Coop.MANAGE)
def run_job(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    func_path = data["task"]

    module_name, func_name = func_path.rsplit(".", 1)

    # Import the module and get the function
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)

    # Create a StringIO object to capture the stdout
    class MultiStream(object):
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for stream in self.streams:
                stream.write(data)

        def flush(self):
            for stream in self.streams:
                stream.flush()

    stdout_capture = StringIO()

    # Create a MultiStream object that writes to both sys.stdout and stdout_capture
    multi_stream = MultiStream(sys.stdout, stdout_capture)

    # Redirect stdout to the StringIO object and call the function
    error = True
    with redirect_stdout(multi_stream):
        try:
            func()
            error = False
        except Exception as e:
            print(f"\nERROR:\n{e}\n")
            for line in traceback.format_exception(type(e), e, e.__traceback__):
                print(line)

    # Get the captured stdout
    captured_stdout = stdout_capture.getvalue()
    return HttpResponse(captured_stdout, status=500 if error else 200)
