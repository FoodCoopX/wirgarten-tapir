from celery import Celery
from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Max

from tapir.wirgarten.models import ScheduledTask
from tapir.wirgarten.service.tasks import schedule_task_unique
from tapir.wirgarten.tasks import send_email_member_contract_end_reminder
from tapir.wirgarten.utils import get_today

app = Celery("tapir", broker=settings.CELERY_BROKER_URL)


class Command(BaseCommand):
    help = "Resets the end of delivery email tasks for all members"

    def handle(self, *args, **options):
        from tapir.wirgarten.models import Member

        celery = app.control.inspect()

        revoked_tasks = set(
            [item for sublist in celery.revoked().values() for item in sublist]
        )

        scheduled_tasks = celery.scheduled()

        self.stdout.write(
            f"Found {len(scheduled_tasks) - len(revoked_tasks)} scheduled tasks"
        )

        tasks_by_member_id = {}
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    if (
                        task["request"]["name"]
                        == "tapir.wirgarten.tasks.send_email_member_contract_end_reminder"
                        and task["request"]["id"] not in revoked_tasks
                    ):
                        member_id = (
                            task["request"]["args"][0]
                            if task["request"]["args"]
                            else task["request"]["kwargs"]["member_id"]
                        )
                        tasks_by_member_id.setdefault(member_id, []).append(task)

        members_with_max_subscription_end_date = Member.objects.annotate(
            max_subscription_end_date=Max("subscription__end_date")
        ).filter(max_subscription_end_date__isnull=False)

        today = get_today()
        ScheduledTask.objects.filter(
            task_function="tapir.wirgarten.tasks.send_email_member_contract_end_reminder"
        ).delete()

        for member in members_with_max_subscription_end_date:
            self.stdout.write(f"\n{member}")
            self.stdout.write(
                f"  Subscription end date: {member.max_subscription_end_date}"
            )
            tasks = tasks_by_member_id.pop(member.id, None)
            if tasks is not None:
                self.stdout.write(f"  Revoking {len(tasks)} scheduled tasks:")
                for task in tasks:
                    self.stdout.write(f"    - {task['eta']}")
                    app.control.revoke(task["request"]["id"], terminate=True)
            else:
                self.stdout.write(self.style.WARNING("  >>> No scheduled tasks found"))

            if member.max_subscription_end_date < today:
                self.stdout.write(
                    self.style.WARNING(
                        "  >>> Subscription already ended, no need to schedule a new task"
                    )
                )
                continue
            else:
                schedule_task_unique(
                    task=send_email_member_contract_end_reminder,
                    eta=member.max_subscription_end_date,
                    kwargs={"member_id": member.id},
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  >>> New task scheduled for {member.max_subscription_end_date}"
                    )
                )
