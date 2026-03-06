import csv
import unicodedata
from csv import DictReader
from decimal import Decimal

import django.db
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import transaction

from tapir.accounts.models import EmailChangeRequest
from tapir.configuration.parameter import get_parameter_value
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_SKIPPED,
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_UPDATED,
)
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.utils.services.member_importer import MemberImporter
from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
    GrowingPeriod,
    Product,
    ProductType,
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
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref


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

            cleaned_headers = [_clean_field_name(h) for h in raw_headers]

            # Continue reading remaining lines as DictReader with the cleaned headers
            reader = csv.DictReader(f, delimiter=";", fieldnames=cleaned_headers)

            # Optional verification mode: show what the importer sees without touching the DB
            if options.get("verify_csv"):
                self.stdout.write(f"Raw headers: {raw_headers}")
                self.stdout.write(f"Cleaned headers: {cleaned_headers}")
                try:
                    first_row = next(reader)
                except StopIteration:
                    self.stdout.write("CSV contains only a header row, no data rows.")
                    return
                self.stdout.write(
                    f"First row (as dict with cleaned headers): {first_row}"
                )
                return
            created = 0
            skipped = 0
            updated = 0

            if import_type == "members":
                if delete_all:
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
                created, skipped, updated = self.import_members(
                    dry_run=dry_run, reader=reader, update_existing=update_existing
                )
            if import_type == "shares":
                if delete_all:
                    TransferCoopSharesLogEntry.objects.all().delete()
                    CoopShareTransaction.objects.all().delete()
                for row in reader:
                    if not any(DataImportUtils.normalize_cell(v) for v in row.values()):
                        continue
                    # {'Mitgliedsnummer': '1', 'Bewegungsart (Z,Ü,K)': 'Z', 'Datum': '2017-03-10', 'Anzahl Anteile': '2', 'Wert Anteile': '100', 'Übertragungspartner': '', 'Wirkung Kündigung': ''}
                    qu = DataImportUtils.safe_int(row.get("Anzahl Anteile"))
                    transfer_member = None
                    valid_date = DataImportUtils.to_date(row.get("Datum"))
                    try:
                        member_no = DataImportUtils.normalize_cell(
                            row.get("Mitgliedsnummer")
                        )
                        member = Member.objects.get(member_no=member_no)
                    except ObjectDoesNotExist:
                        self.stderr.write(str(row))
                        self.stderr.write("Database Error: Member not found")
                        continue
                    if (
                        DataImportUtils.normalize_cell(row.get("Übertragungspartner"))
                        != ""
                    ):
                        try:
                            transfer_member = Member.objects.get(
                                member_no=DataImportUtils.normalize_cell(
                                    row.get("Übertragungspartner")
                                )
                            )
                        except ObjectDoesNotExist:
                            self.stderr.write(str(row))
                            self.stderr.write("Transfer Member not found!")
                            continue
                    match DataImportUtils.normalize_cell(
                        row.get("Bewegungsart (Z,Ü,K)")
                    ):
                        case "Z":
                            trans_type = (
                                CoopShareTransaction.CoopShareTransactionType.PURCHASE
                            )
                        case "Ü":
                            if qu > 0:
                                trans_type = (
                                    CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN
                                )
                            else:
                                trans_type = (
                                    CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT
                                )
                        case "K":
                            trans_type = (
                                CoopShareTransaction.CoopShareTransactionType.CANCELLATION
                            )
                            valid_date = DataImportUtils.to_date(
                                row.get("Wirkung Kündigung")
                            )
                        case _:
                            raise ValueError("Unknown transaction type!")

                    timestamp = DataImportUtils.to_datetime_from_date(
                        row.get("Datum"), hour=0, minute=0
                    )

                    # Check for existing transaction
                    existing_trans = CoopShareTransaction.objects.filter(
                        member=member,
                        transaction_type=trans_type,
                        timestamp=timestamp,
                    ).first()

                    if existing_trans:
                        if not update_existing:
                            skipped += 1
                            continue

                        # Update if different
                        is_updated = False
                        if existing_trans.transfer_member != transfer_member:
                            existing_trans.transfer_member = transfer_member
                            is_updated = True
                        if existing_trans.quantity != qu:
                            existing_trans.quantity = qu
                            is_updated = True
                        if existing_trans.valid_at != valid_date:
                            existing_trans.valid_at = valid_date
                            is_updated = True
                        share_price = Decimal(
                            get_parameter_value(
                                key=ParameterKeys.COOP_SHARE_PRICE, cache={}
                            )
                        )
                        if existing_trans.share_price != share_price:
                            existing_trans.share_price = share_price
                            is_updated = True

                        if is_updated:
                            try:
                                if not dry_run:
                                    existing_trans.save()
                                updated += 1
                            except Exception as e:
                                self.stderr.write(
                                    f"Error updating share transaction: {e}"
                                )
                                skipped += 1
                        else:
                            skipped += 1
                        continue

                    try:
                        if dry_run:
                            created += 1
                        else:
                            with transaction.atomic():
                                CoopShareTransaction.objects.create(
                                    member_id=member.id,
                                    transaction_type=trans_type,
                                    timestamp=timestamp,
                                    valid_at=valid_date,
                                    quantity=qu,
                                    share_price=get_parameter_value(
                                        key=ParameterKeys.COOP_SHARE_PRICE, cache={}
                                    ),
                                    transfer_member=transfer_member,
                                )
                            created += 1
                    except django.db.Error as e:
                        self.stderr.write(str(row))
                        self.stderr.write(f"Database Error occured {e.__cause__}")
                        skipped += 1
                    except ValidationError as e:
                        self.stderr.write(str(row))
                        self.stderr.write(f"Validation Error occured {e.messages}")
                        skipped += 1
            if import_type == "subscriptions":
                if delete_all:
                    SolidarityContribution.objects.all().delete()
                    SubscriptionChangeLogEntry.objects.all().delete()
                    Subscription.objects.all().delete()
                    Payment.objects.all().delete()
                # for row in reader:
                for row in reader:
                    if not any(DataImportUtils.normalize_cell(v) for v in row.values()):
                        continue
                    # VertragNr,Zeitstempel,E-Mail-Adresse,Tapir-ID,Mitgliedernummer,Probevertrag,Vertragsbeginn,[S-Ernteanteil],[M-Ernteanteil],[L-Ernteanteil],[XL-Ernteanteil],product,Quantity,"Gesamtzahlung",Vertragsgrundsätze,Abholort,Email-Adressen,Ernteanteilsreduzierung/erhöhung,consent_widerruf,consent_vertragsgrundsätze,cancellation.ts
                    # print(row)
                    # identify MemberID, either via MemberNo or Email
                    try:
                        start_date = DataImportUtils.to_date(row.get("Vertragsbeginn"))
                        if not start_date:
                            self.stderr.write(str(row))
                            self.stderr.write(
                                "No start_date (Vertragsbeginn) found. Skipping row."
                            )
                            continue

                        # identify GrowingPeriod from start_date
                        period = GrowingPeriod.objects.filter(
                            start_date__lte=start_date, end_date__gte=start_date
                        ).first()

                        if not period:
                            # Fallback: find the next possible growing period
                            period = (
                                GrowingPeriod.objects.filter(start_date__gte=start_date)
                                .order_by("start_date")
                                .first()
                            )

                        if not period:
                            self.stderr.write(str(row))
                            self.stderr.write(
                                f"No GrowingPeriod found for start_date {start_date}. Skipping row."
                            )
                            continue

                        if (
                            DataImportUtils.normalize_cell(row.get("Mitgliedernummer"))
                            != ""
                        ):
                            member_no = DataImportUtils.normalize_cell(
                                row.get("Mitgliedernummer")
                            )
                            try:
                                m = Member.objects.get(member_no=int(member_no))
                            except ValueError:
                                self.stderr.write(str(row))
                                self.stderr.write(
                                    f"Invalid member number: {member_no}. Skipping row."
                                )
                                continue
                        else:
                            if DataImportUtils.normalize_cell(row.get("Email")) != "":
                                m = Member.objects.get(
                                    email=DataImportUtils.normalize_cell(
                                        row.get("Email")
                                    )
                                )
                            else:
                                self.stderr.write(str(row))
                                self.stderr.write(
                                    f"No data to identify Member in subscription for {row.get('Mitgliedernummer')} {row.get('Email')}"
                                )
                    except django.core.exceptions.ObjectDoesNotExist:
                        self.stderr.write(str(row))
                        self.stderr.write("Database Error: Member not found")
                        continue
                    except django.db.Error as e:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            f"Database Error occured with MemberNo {e.__cause__}"
                        )
                        continue
                    except ValidationError as e:
                        self.stderr.write(str(row))
                        self.stderr.write(f"Validation Error occured {e.messages}")
                        continue
                    # identify MandateRef
                    mref = get_or_create_mandate_ref(m)
                    # identify product
                    try:
                        product_name = DataImportUtils.normalize_cell(
                            row.get("product")
                        )
                        product_type_name = DataImportUtils.normalize_cell(
                            row.get("product_type")
                        )

                        if product_name:
                            filter_kwargs = {"name": product_name}
                            if product_type_name:
                                try:
                                    ptype = ProductType.objects.get(
                                        name=product_type_name
                                    )
                                    filter_kwargs["type"] = ptype
                                except ProductType.DoesNotExist:
                                    self.stderr.write(str(row))
                                    self.stderr.write(
                                        f"ProductType '{product_type_name}' not found"
                                    )
                                    continue

                            prod = Product.objects.get(**filter_kwargs)
                        else:
                            self.stderr.write(str(row))
                            self.stderr.write("No product defined in subscription.")
                            continue
                    except Product.DoesNotExist:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            f"Product '{product_name}' (Type: {product_type_name or 'any'}) not found"
                        )
                        continue
                    except Product.MultipleObjectsReturned:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            f"Multiple products found for name '{product_name}'. Please specify 'product_type'."
                        )
                        continue
                    except django.core.exceptions.ObjectDoesNotExist as e:
                        self.stderr.write(str(row))
                        self.stderr.write(f"Error finding product: {e}")
                        continue
                    # prepare cancellation value
                    if DataImportUtils.normalize_cell(row.get("cancellation.ts")) != "":
                        ts_cancel = DataImportUtils.to_datetime(
                            row.get("cancellation.ts")
                        ) or DataImportUtils.to_datetime_from_date(
                            row.get("cancellation.ts")
                        )
                    else:
                        ts_cancel = None

                    # parse optional trial fields
                    trial_period_is_enabled = DataImportUtils.safe_bool(
                        row.get("Probezeit")
                    )
                    trial_end_date_override = DataImportUtils.to_date(
                        row.get("Ende Probezeit (Sonntag)")
                    )

                    quantity = DataImportUtils.safe_float(row.get("Quantity"))
                    v_start_date = DataImportUtils.to_date(row.get("Vertragsbeginn"))
                    v_end_date = DataImportUtils.to_date(row.get("Vertragsende"))
                    consent_ts = DataImportUtils.to_datetime(
                        row.get("consent_vertragsgrundsätze")
                    ) or DataImportUtils.to_datetime_from_date(
                        row.get("consent_vertragsgrundsätze")
                    )
                    withdrawal_consent_ts = DataImportUtils.to_datetime(
                        row.get("consent_widerruf")
                    ) or DataImportUtils.to_datetime_from_date(
                        row.get("consent_widerruf")
                    )

                    # Check for existing subscription
                    filter_criteria = {
                        "member": m,
                        "product": prod,
                        "period": period,
                        "start_date": v_start_date,
                    }
                    if product_type_name:
                        filter_criteria["product__type"] = prod.type

                    existing_sub = Subscription.objects.filter(
                        **filter_criteria
                    ).first()

                    if existing_sub:
                        if not update_existing:
                            skipped += 1
                            continue

                        # Update if different
                        is_updated = False

                        def _update_if_diff(obj, field, new_val):
                            old_val = getattr(obj, field)
                            if new_val != old_val:
                                setattr(obj, field, new_val)
                                return True
                            return False

                        if _update_if_diff(existing_sub, "quantity", quantity):
                            is_updated = True
                        if _update_if_diff(existing_sub, "end_date", v_end_date):
                            is_updated = True
                        if _update_if_diff(existing_sub, "cancellation_ts", ts_cancel):
                            is_updated = True
                        if _update_if_diff(existing_sub, "consent_ts", consent_ts):
                            is_updated = True
                        if _update_if_diff(
                            existing_sub, "withdrawal_consent_ts", withdrawal_consent_ts
                        ):
                            is_updated = True
                        if trial_period_is_enabled is not None:
                            if _update_if_diff(
                                existing_sub,
                                "trial_disabled",
                                not trial_period_is_enabled,
                            ):
                                is_updated = True
                        if _update_if_diff(
                            existing_sub,
                            "trial_end_date_override",
                            trial_end_date_override,
                        ):
                            is_updated = True

                        if is_updated:
                            try:
                                if not dry_run:
                                    existing_sub.save()
                                updated += 1
                            except Exception as e:
                                self.stderr.write(f"Error updating subscription: {e}")
                                skipped += 1
                        else:
                            skipped += 1
                        continue

                    try:
                        if dry_run:
                            created += 1
                        else:
                            with transaction.atomic():
                                Subscription.objects.create(
                                    member_id=m.id,
                                    quantity=quantity,
                                    start_date=v_start_date,
                                    end_date=v_end_date,
                                    cancellation_ts=ts_cancel,
                                    mandate_ref_id=mref.ref,
                                    period_id=period.id,
                                    product_id=prod.id,
                                    consent_ts=consent_ts,
                                    withdrawal_consent_ts=withdrawal_consent_ts,
                                    trial_disabled=(
                                        not trial_period_is_enabled
                                        if trial_period_is_enabled is not None
                                        else False
                                    ),
                                    trial_end_date_override=trial_end_date_override,
                                    notice_period_duration=NoticePeriodManager.get_notice_period_duration(
                                        prod.type, period, {}
                                    ),
                                    notice_period_unit=NoticePeriodManager.get_notice_period_unit(
                                        prod.type, period, {}
                                    ),
                                )
                            created += 1
                        # print("Subscription object successfully created.")
                    except django.db.Error as e:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            f"Database Error occured with create subscription: {e.__cause__}"
                        )
                        skipped += 1
                        continue
                    except ValidationError as e:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            f"Validation Error occured with create subscription: {e.messages}"
                        )
                        skipped += 1
                        continue
                    except ValueError as e:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            f"Value Error occured with create subscription: {e}"
                        )
                        skipped += 1
                        continue

            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}"
                )
            )

    def import_members(
        self, dry_run: bool, reader: DictReader[str], update_existing: bool
    ):
        skipped = 0
        created = 0
        updated = 0

        for row_index, row in enumerate(reader):
            try:
                import_status = self.import_member(
                    row=row, update_existing=update_existing, dry_run=dry_run
                )

                if import_status == MEMBER_IMPORT_STATUS_SKIPPED:
                    skipped += 1
                if import_status == MEMBER_IMPORT_STATUS_CREATED:
                    created += 1
                if import_status == MEMBER_IMPORT_STATUS_UPDATED:
                    updated += 1

            except Exception as e:
                self.stderr.write(
                    f"Error while importing row with internal index {row_index} (should be line {row_index+2} in the file): {e}"
                )
                skipped += 1
                continue

        return created, skipped, updated

    @transaction.atomic
    def import_member(self, row: dict[str, str], update_existing: bool, dry_run: bool):
        # skip empty lines
        if not any(DataImportUtils.normalize_cell(v) for v in row.values()):
            return None

        member_no = int(DataImportUtils.normalize_cell(row.get("Nr")))
        member = Member.objects.filter(member_no=member_no).first()

        if member:
            if not update_existing:
                return MEMBER_IMPORT_STATUS_SKIPPED

            try:
                return MemberImporter.update_existing_member_if_necessary(
                    member=member, row=row, dry_run=dry_run
                )
            except Exception as e:
                self.stderr.write(f"Error updating member {member_no}: {e}")
                return MEMBER_IMPORT_STATUS_SKIPPED

        try:
            return MemberImporter.create_new_member(
                member_no=member_no, row=row, dry_run=dry_run
            )
        except Exception as e:
            self.stderr.write(f"Error creating member {member_no}: {e}")
            return MEMBER_IMPORT_STATUS_SKIPPED
