import csv
import os
import sys
import traceback
import unicodedata
from csv import DictReader
from typing import Literal

from django.core.management import BaseCommand
from django.db import transaction
from icecream import ic

from tapir.accounts.models import EmailChangeRequest
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_SKIPPED,
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_UPDATED,
)
from tapir.utils.exceptions import DryRunException
from tapir.utils.services.member_importer import MemberImporter
from tapir.utils.services.share_importer import ShareImporter
from tapir.utils.services.subscription_importer import SubscriptionImporter
from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
    MandateReference,
    MemberPickupLocation,
    Payment,
    LogEntry,
    QuestionaireCancellationReasonResponse,
    QuestionaireTrafficSourceResponse,
    WaitingListEntry,
    TransferCoopSharesLogEntry,
    SubscriptionChangeLogEntry,
)


class Command(BaseCommand):
    help = "Imports data from CSV files into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type", nargs=1, choices=["members", "shares", "subscriptions"]
        )
        parser.add_argument("--file", nargs=1)
        parser.add_argument("--delete-all", action="store_true")
        parser.add_argument("--reset-all", action="store_true")
        parser.add_argument(
            "--verify-csv",
            action="store_true",
            help=(
                "Read the CSV, normalize headers, print raw/cleaned headers and the first row, then exit "
                "(no database writes)."
            ),
        )
        parser.add_argument(
            "--update",
            nargs=1,
            choices=["yes", "no"],
            default=["no"],
            help="Update existing records if differences are found (yes/no). Default: no.",
        )

        parser.add_argument(
            "--dry-run", action="store_true", help="If enabled, no change will be saved"
        )

        parser.add_argument(
            "--stacktrace",
            action="store_true",
            help="If enabled, will print the stacktrace for all errors. Otherwise, only a short summary will be printed",
        )

    def handle(self, *args, **options):
        # Helper functions

        if options["reset_all"]:
            SolidarityContribution.objects.all().delete()
            SubscriptionChangeLogEntry.objects.all().delete()
            TransferCoopSharesLogEntry.objects.all().delete()
            CoopShareTransaction.objects.all().delete()
            Subscription.objects.all().delete()
            Payment.objects.all().delete()
            MandateReference.objects.all().delete()
            MemberPickupLocation.objects.all().delete()
            LogEntry.objects.all().delete()
            QuestionaireCancellationReasonResponse.objects.all().delete()
            QuestionaireTrafficSourceResponse.objects.all().delete()
            WaitingListEntry.objects.all().delete()
            EmailChangeRequest.objects.all().delete()
            Member.objects.all().delete()
            return

        # check if type and file params are present
        if (
            not options.get("file")
            or not options["file"][0]
            or not options.get("type")
            or not options["type"][0]
        ):
            self.stderr.write(
                "If not --reset-all is used, parameters --type and --file must be present."
            )
            return

        filepath = options["file"][0]
        import_type = options["type"][0]
        delete_all = options["delete_all"]
        dry_run = options.get("dry_run", False)
        print_stacktrace = options.get("stacktrace", False)
        update_existing = options.get("update")[0] == "yes"

        # Open with utf-8-sig so a potential BOM (U+FEFF) is discarded automatically
        # Normalize/clean header names to remove invisible/odd whitespace
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            base_reader = csv.reader(f, delimiter=";")

            try:
                raw_headers = next(base_reader)
            except StopIteration:
                print("Provided CSV file is empty.")
                return

            cleaned_headers = [self._clean_field_name(h) for h in raw_headers]

            # Continue reading remaining lines as DictReader with the cleaned headers
            reader = csv.DictReader(f, delimiter=";", fieldnames=cleaned_headers)

            # Optional verification mode: show what the importer sees without touching the DB
            if options.get("verify_csv"):
                self.verify_csv(cleaned_headers, raw_headers, reader)
                return

            try:
                with transaction.atomic():
                    if delete_all:
                        if import_type == "members":
                            SolidarityContribution.objects.all().delete()
                            SubscriptionChangeLogEntry.objects.all().delete()
                            TransferCoopSharesLogEntry.objects.all().delete()
                            CoopShareTransaction.objects.all().delete()
                            Subscription.objects.all().delete()
                            Payment.objects.all().delete()
                            MandateReference.objects.all().delete()
                            MemberPickupLocation.objects.all().delete()
                            LogEntry.objects.all().delete()
                            QuestionaireCancellationReasonResponse.objects.all().delete()
                            QuestionaireTrafficSourceResponse.objects.all().delete()
                            WaitingListEntry.objects.all().delete()
                            EmailChangeRequest.objects.all().delete()
                            Member.objects.all().delete()

                        if import_type == "shares":
                            TransferCoopSharesLogEntry.objects.all().delete()
                            CoopShareTransaction.objects.all().delete()

                        if import_type == "subscriptions":
                            SubscriptionChangeLogEntry.objects.all().delete()
                            Subscription.objects.all().delete()
                            Payment.objects.all().delete()

                    self.import_generic(
                        reader=reader,
                        update_existing=update_existing,
                        import_type=import_type,
                        print_stacktrace=print_stacktrace,
                    )
                    if dry_run:
                        raise DryRunException()
            except DryRunException:
                pass

    def verify_csv(
        self,
        cleaned_headers: list[str | None],
        raw_headers: list[str],
        reader: DictReader[str | None],
    ):
        self.stdout.write(f"Raw headers: {raw_headers}")
        self.stdout.write(f"Cleaned headers: {cleaned_headers}")
        try:
            first_row = next(reader)
        except StopIteration:
            self.stdout.write("CSV contains only a header row, no data rows.")
            return
        self.stdout.write(f"First row (as dict with cleaned headers): {first_row}")

    def print_results(self, created: int, updated: int, skipped: int):
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}"
            )
        )

    def import_generic(
        self,
        reader: DictReader[str],
        update_existing: bool,
        import_type: Literal["members", "shares", "subscriptions"],
        print_stacktrace: bool,
    ):
        skipped = 0
        created = 0
        updated = 0

        for row_index, row in enumerate(reader):
            try:
                match import_type:
                    case "members":
                        method = MemberImporter.import_member
                    case "shares":
                        method = ShareImporter.import_shares_single_member
                    case "subscriptions":
                        method = SubscriptionImporter.import_subscription

                with transaction.atomic():
                    import_status = method(row=row, update_existing=update_existing)

                if import_status == MEMBER_IMPORT_STATUS_SKIPPED:
                    skipped += 1
                if import_status == MEMBER_IMPORT_STATUS_CREATED:
                    created += 1
                if import_status == MEMBER_IMPORT_STATUS_UPDATED:
                    updated += 1

            except Exception as exception:
                self.stderr.write(
                    f"Error while importing row with internal index {row_index} (should be line {row_index+2} in the file), import type: {import_type}"
                )
                self.print_exception_details(exception, print_stacktrace)
                self.stderr.write(ic.format(row))
                skipped += 1
                continue

        self.print_results(created=created, updated=updated, skipped=skipped)

    def print_exception_details(self, exception, print_stacktrace: bool):
        _, _, exception_traceback = sys.exc_info()
        exception_filename = os.path.split(
            exception_traceback.tb_frame.f_code.co_filename
        )[1]
        exception_line_number = exception_traceback.tb_lineno
        self.stderr.write(f"{exception}, {exception_filename}:L{exception_line_number}")
        if print_stacktrace:
            self.stderr.write(traceback.format_exc())

    @staticmethod
    def _clean_field_name(s: str) -> str | None:
        if s is None:
            return s
        # Remove common invisible characters and normalize
        # - BOM (\ufeff), zero-width spaces (\u200b, \u200c, \u200d), word joiner (\u2060)
        # - Non-breaking space (\u00a0) -> regular space
        s = (
            s.replace("\ufeff", "")
            .replace("\u200b", "")
            .replace("\u200c", "")
            .replace("\u200d", "")
            .replace("\u2060", "")
            .replace("\xa0", " ")
        )
        s = unicodedata.normalize("NFKC", s)
        return s.strip()
