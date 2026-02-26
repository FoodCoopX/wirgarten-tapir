import csv
import datetime
import unicodedata

import django.db
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
    GrowingPeriod,
    Product,
    ProductType,
    PickupLocation,
    MandateReference,
    MemberPickupLocation,
    Payment,
    LogEntry,
    QuestionaireCancellationReasonResponse,
    QuestionaireTrafficSourceResponse,
    WaitingListEntry,
)
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.accounts.models import EmailChangeRequest


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
            "--growing-period-start",
            type=str,
            help="Start date of the growing period to use for subscriptions (format: YYYY-MM-DD)",
        )
        parser.add_argument(
            "--verify-csv",
            action="store_true",
            help=(
                "Read the CSV, normalize headers, print raw/cleaned headers and the first row, then exit "
                "(no database writes)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and simulate the import without writing to the database.",
        )

    def handle(self, *args, **options):
        # Helper functions
        def _normalize_cell(v):
            if v is None:
                return ""
            if isinstance(v, str):
                return v.strip()
            return v

        def _safe_int(v, default=0):
            v = _normalize_cell(v)
            try:
                return int(v)
            except (TypeError, ValueError):
                return default

        def _safe_float(v, default=0.0):
            v = _normalize_cell(v)
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        def _safe_bool(v):
            v = _normalize_cell(v)
            if v == "":
                return None
            s = str(v).strip().lower()
            return s in ("1", "true", "yes", "ja", "j", "y", "x")

        def _to_date(v):
            v = _normalize_cell(v)
            if not v:
                return None
            d = parse_date(v)
            return d

        def _to_datetime_from_date(v, hour=12, minute=0, tz=None):
            # Interpret a date string as a datetime at given hour in the provided/current tz
            d = _to_date(v)
            if not d:
                return None
            tzinfo = tz or timezone.get_current_timezone()
            return timezone.make_aware(
                datetime.datetime(d.year, d.month, d.day, hour, minute), tzinfo
            )

        def _to_datetime(v):
            v = _normalize_cell(v)
            if not v:
                return None
            # Try parse full datetime first, then date-only
            dt = parse_datetime(v)
            if dt is None:
                return _to_datetime_from_date(v)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

        if options["reset_all"]:
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

        # Open with utf-8-sig so a potential BOM (U+FEFF) is discarded automatically
        # Normalize/clean header names to remove invisible/odd whitespace
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            base_reader = csv.reader(f, delimiter=";")

            try:
                raw_headers = next(base_reader)
            except StopIteration:
                print("Provided CSV file is empty.")
                return

            def _clean_field_name(s: str) -> str:
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
                    EmailChangeRequest.objects.all().delete()
                    Member.objects.all().delete()
                for row in reader:
                    # skip empty lines
                    if not any(_normalize_cell(v) for v in row.values()):
                        continue
                    # identify pickup location ID
                    try:
                        if _normalize_cell(row.get("Abholort")) != "":
                            picloc = PickupLocation.objects.get(
                                name=_normalize_cell(row.get("Abholort"))
                            )
                        else:
                            picloc = None
                    except ObjectDoesNotExist as e:
                        self.stderr.write(str(row))
                        self.stderr.write(
                            "Pickup Location not found - record is skipped!"
                        )
                        continue
                    m = Member(
                        first_name=_normalize_cell(row.get("Vorname")),
                        last_name=_normalize_cell(row.get("Nachname")),
                        birthdate=_to_date(row.get("Geburtstag/Gründungsdatum")),
                        form_of_address=_normalize_cell(row.get("Anrede")),
                        street=" ".join(
                            s.rstrip()
                            for s in [
                                _normalize_cell(row.get("Straße")),
                                _normalize_cell(row.get("Hausnr.")),
                            ]
                            if s and s.rstrip() != ""
                        ),
                        postcode=_normalize_cell(row.get("PLZ")),
                        city=_normalize_cell(row.get("Ort")),
                        email=_normalize_cell(row.get("Mailadresse")),
                        phone_number=_normalize_cell(row.get("Telefon")),
                        phone_number_landline=_normalize_cell(row.get("Telefon 2")),
                        member_no=_normalize_cell(row.get("Nr")),
                        iban=_normalize_cell(row.get("IBAN")),
                        account_owner=_normalize_cell(row.get("Kontoinhaber")),
                        sepa_consent=_to_datetime(row.get("consent_sepa")),
                        privacy_consent=_to_datetime(row.get("privacy_consent")),
                    )
                    mp = MemberPickupLocation(
                        member=m,
                        pickup_location=picloc,
                        valid_from=_to_date(row.get("AO_gueltig_ab")),
                    )
                    # Persists member and pickup location transactionally; handles errors
                    try:
                        if dry_run:
                            created += 1
                        else:
                            with transaction.atomic():
                                m.save(bypass_keycloak=True)
                                if picloc is not None:
                                    mp.save()
                            created += 1
                    except Exception as e:
                        self.stderr.write(str(e))
                        skipped += 1
                        continue
            if import_type == "shares":
                if delete_all:
                    CoopShareTransaction.objects.all().delete()
                for row in reader:
                    if not any(_normalize_cell(v) for v in row.values()):
                        continue
                    # print(row)
                    # {'Mitgliedsnummer': '1', 'Bewegungsart (Z,Ü,K)': 'Z', 'Datum': '2017-03-10', 'Anzahl Anteile': '2', 'Wert Anteile': '100', 'Übertragungspartner': '', 'Wirkung Kündigung': ''}
                    qu = _safe_int(row.get("Anzahl Anteile"))
                    transfer_member = None
                    valid_date = _to_date(row.get("Datum"))
                    try:
                        member_no = _normalize_cell(row.get("Mitgliedsnummer"))
                        member = Member.objects.get(member_no=member_no)
                    except ObjectDoesNotExist as e:
                        self.stderr.write(str(row))
                        self.stderr.write("Database Error: Member not found")
                        continue
                    if _normalize_cell(row.get("Übertragungspartner")) != "":
                        try:
                            transfer_member = Member.objects.get(
                                member_no=_normalize_cell(
                                    row.get("Übertragungspartner")
                                )
                            )
                        except ObjectDoesNotExist as e:
                            self.stderr.write(str(row))
                            self.stderr.write("Transfer Member not found!")
                            continue
                    match _normalize_cell(row.get("Bewegungsart (Z,Ü,K)")):
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
                            valid_date = _to_date(row.get("Wirkung Kündigung"))
                        case _:
                            raise ValueError("Unknown transaction type!")
                    try:
                        if dry_run:
                            created += 1
                        else:
                            with transaction.atomic():
                                CoopShareTransaction.objects.create(
                                    member_id=member.id,
                                    transaction_type=trans_type,
                                    timestamp=_to_datetime_from_date(
                                        row.get("Datum"), hour=0, minute=0
                                    ),
                                    valid_at=valid_date,
                                    quantity=qu,
                                    share_price=50,
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
                    Subscription.objects.all().delete()
                    # identify current growing_period
                # Growing Period handling
                if options.get("growing_period_start"):
                    start_date_str = options["growing_period_start"]

                    # Validiere Datumsformat
                    try:
                        datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
                    except ValueError:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Invalid date format '{start_date_str}'. Please use YYYY-MM-DD format (e.g., 2023-01-01)."
                            )
                        )
                        return

                    try:
                        period = GrowingPeriod.objects.get(start_date=start_date_str)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Using GrowingPeriod: ID={period.id}, Start={period.start_date}"
                            )
                        )
                    except GrowingPeriod.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"GrowingPeriod with start_date='{options['growing_period_start']}' does not exist!"
                            )
                        )
                        self.stdout.write("Available GrowingPeriods:")
                        for gp in GrowingPeriod.objects.all():
                            self.stdout.write(
                                f"  - ID: {gp.id}, Start: {gp.start_date}, End: {gp.end_date}"
                            )
                        return
                    except ValueError as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Invalid date format '{options['growing_period_start']}'. Use YYYY-MM-DD format."
                            )
                        )
                        return
                else:
                    # Fallback: Ersten verfügbaren GrowingPeriod verwenden
                    period = GrowingPeriod.objects.first()
                    if not period:
                        self.stdout.write(
                            self.style.ERROR(
                                "No GrowingPeriod exists! Please create one first or specify --growing-period-start."
                            )
                        )
                        return
                    self.stdout.write(
                        self.style.WARNING(
                            f"No --growing-period-start specified. Using first available: "
                            f"ID={period.id}, Start={period.start_date}"
                        )
                    )
                for row in reader:
                    if not any(_normalize_cell(v) for v in row.values()):
                        continue
                    # VertragNr,Zeitstempel,E-Mail-Adresse,Tapir-ID,Mitgliedernummer,Probevertrag,Vertragsbeginn,[S-Ernteanteil],[M-Ernteanteil],[L-Ernteanteil],[XL-Ernteanteil],product,Quantity,Richtpreis,Solidarpreis in Prozent,"Gesamtzahlung",Vertragsgrundsätze,Abholort,Email-Adressen,Ernteanteilsreduzierung/erhöhung,consent_widerruf,consent_vertragsgrundsätze,cancellation.ts
                    # print(row)
                    # identify MemberID, either via MemberNo or Email
                    try:
                        if _normalize_cell(row.get("Mitgliedernummer")) != "":
                            m = Member.objects.get(
                                member_no=_normalize_cell(row.get("Mitgliedernummer"))
                            )
                        else:
                            if _normalize_cell(row.get("Email")) != "":
                                m = Member.objects.get(
                                    email=_normalize_cell(row.get("Email"))
                                )
                            else:
                                self.stderr.write(str(row))
                                self.stderr.write(
                                    f"No data to identify Member in subscription for {row.get('Mitgliedernummer')} {row.get('Email')}"
                                )
                    except django.core.exceptions.ObjectDoesNotExist as e:
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
                        product_name = _normalize_cell(row.get("product"))
                        product_type_name = _normalize_cell(row.get("product_type"))

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
                    if _normalize_cell(row.get("cancellation.ts")) != "":
                        ts_cancel = _to_datetime(
                            row.get("cancellation.ts")
                        ) or _to_datetime_from_date(row.get("cancellation.ts"))
                    else:
                        ts_cancel = None

                    # parse optional trial fields
                    trial_disabled_val = _safe_bool(row.get("trial_disabled"))
                    trial_end_date_override = _to_date(
                        row.get("trial_end_date_override")
                    )

                    try:
                        if dry_run:
                            created += 1
                        else:
                            with transaction.atomic():
                                Subscription.objects.create(
                                    member_id=m.id,
                                    quantity=_safe_float(row.get("Quantity")),
                                    start_date=_to_date(row.get("Vertragsbeginn")),
                                    end_date=_to_date(row.get("Vertragsende")),
                                    cancellation_ts=ts_cancel,
                                    mandate_ref_id=mref.ref,
                                    period_id=period.id,
                                    product_id=prod.id,
                                    consent_ts=_to_datetime(
                                        row.get("consent_vertragsgrundsätze")
                                    )
                                    or _to_datetime_from_date(
                                        row.get("consent_vertragsgrundsätze")
                                    ),
                                    withdrawal_consent_ts=_to_datetime(
                                        row.get("consent_widerruf")
                                    )
                                    or _to_datetime_from_date(
                                        row.get("consent_widerruf")
                                    ),
                                    trial_disabled=(
                                        trial_disabled_val
                                        if trial_disabled_val is not None
                                        else False
                                    ),
                                    trial_end_date_override=trial_end_date_override,
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
