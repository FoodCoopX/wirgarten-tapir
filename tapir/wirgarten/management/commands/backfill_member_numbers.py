from django.core.management.base import BaseCommand
from django.db import transaction

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member


class Command(BaseCommand):
    help = "Assigns member numbers to existing members that don't have one. "

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't save anything, only show which members would get a number.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        members_without_number = Member.objects.filter(member_no__isnull=True).order_by(
            "created_at", "id"
        )
        total = members_without_number.count()
        self.stdout.write(f"Members without number: {total}")

        assigned = 0
        skipped = 0

        try:
            with transaction.atomic():
                for member in members_without_number:
                    if MemberNumberService.should_assign_member_no(member):
                        if not dry_run:
                            MemberNumberService.assign_member_no_if_eligible(member)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  {'[dry-run] ' if dry_run else ''}{member}"
                            )
                        )
                        assigned += 1
                    else:
                        skipped += 1

                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            pass  # Intentional: rollback atomic transaction in dry-run mode

        verb = "would be assigned" if dry_run else "assigned"
        self.stdout.write(
            self.style.SUCCESS(f"Done: {assigned} numbers {verb}, {skipped} skipped.")
        )


class _DryRunRollback(Exception):
    pass
