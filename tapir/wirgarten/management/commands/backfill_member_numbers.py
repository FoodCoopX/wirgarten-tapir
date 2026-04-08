"""
One-off command to assign member numbers to pre-existing members that
don't have one yet.

Rationale (US 4.3 / #535): we deliberately chose *not* to backfill via a
Django data migration because:

- The start value of the counter is an admin decision and should be set
  in the admin UI *before* the backfill runs. A data migration would run
  blindly at ``migrate`` time with whichever default is in place.
- The backfill has to honour the full business logic (trial toggle,
  coop-trial check, subscription-trial check). A data migration going
  through ``apps.get_model()`` cannot easily re-use the service layer.

This command is idempotent — running it twice is harmless because
``assign_member_no_if_eligible`` never overwrites an existing number.

Usage (in Docker):

    docker compose exec web poetry run python manage.py backfill_member_numbers --dry-run
    docker compose exec web poetry run python manage.py backfill_member_numbers
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from tapir.wirgarten.models import Member
from tapir.wirgarten.service.member_numbers import (
    assign_member_no_if_eligible,
    compute_next_member_no,
    should_assign_member_no,
)


class Command(BaseCommand):
    help = (
        "Assigns member numbers to existing members that don't have one. "
        "Respects the 'Assign during trial' toggle and the configured start "
        "value. Idempotent — can be run multiple times without harm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't save anything, only show which members would get a number.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        # Order by creation time + id so dry-run and real run are stable and
        # the assigned numbers are monotonic with creation order.
        missing = Member.objects.filter(member_no__isnull=True).order_by(
            "created_at", "id"
        )
        total = missing.count()
        self.stdout.write(f"Members without number: {total}")

        assigned = 0
        skipped = 0

        # We simulate the counter locally during dry-run so users see the
        # actual numbers that *would* be assigned (MAX+1 advances as we go).
        simulated_next = compute_next_member_no() if dry_run else None

        for member in missing:
            if dry_run:
                if should_assign_member_no(member):
                    self.stdout.write(
                        f"  [dry-run] {member} would get number {simulated_next}"
                    )
                    simulated_next += 1
                    assigned += 1
                else:
                    self.stdout.write(f"  [dry-run] {member} would be skipped (trial)")
                    skipped += 1
            else:
                with transaction.atomic():
                    if assign_member_no_if_eligible(member):
                        self.stdout.write(self.style.SUCCESS(f"  {member}"))
                        assigned += 1
                    else:
                        skipped += 1

        verb = "would be assigned" if dry_run else "assigned"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {assigned} numbers {verb}, {skipped} skipped "
                f"(trial toggle or already present)."
            )
        )
