import csv
import datetime
import unicodedata

import django.db
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from tapir.utils.models import MemberImportedLogEntry
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
    TransferCoopSharesLogEntry,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.accounts.models import EmailChangeRequest
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.utils import get_today


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
                    member_no = _normalize_cell(row.get("Nr"))
                    m = None
                    if member_no:
                        try:
                            m = Member.objects.get(member_no=member_no)
                        except Member.DoesNotExist:
                            pass

                    if m:
                        if not update_existing:
                            skipped += 1
                            continue

                        # Update logic
                        updated_fields = []

                        def _update_if_diff(obj, field, new_val):
                            old_val = getattr(obj, field)
                            if new_val != old_val:
                                setattr(obj, field, new_val)
                                return True
                            return False

                        if _update_if_diff(
                            m, "first_name", _normalize_cell(row.get("Vorname"))
                        ):
                            updated_fields.append("first_name")
                        if _update_if_diff(
                            m, "last_name", _normalize_cell(row.get("Nachname"))
                        ):
                            updated_fields.append("last_name")
                        if _update_if_diff(
                            m,
                            "birthdate",
                            _to_date(row.get("Geburtstag/Gründungsdatum")),
                        ):
                            updated_fields.append("birthdate")
                        if _update_if_diff(
                            m, "form_of_address", _normalize_cell(row.get("Anrede"))
                        ):
                            updated_fields.append("form_of_address")

                        new_street = " ".join(
                            s.rstrip()
                            for s in [
                                _normalize_cell(row.get("Straße")),
                                _normalize_cell(row.get("Hausnr.")),
                            ]
                            if s and s.rstrip() != ""
                        )
                        if _update_if_diff(m, "street", new_street):
                            updated_fields.append("street")

                        if _update_if_diff(
                            m, "postcode", _normalize_cell(row.get("PLZ"))
                        ):
                            updated_fields.append("postcode")
                        if _update_if_diff(m, "city", _normalize_cell(row.get("Ort"))):
                            updated_fields.append("city")
                        if _update_if_diff(
                            m, "email", _normalize_cell(row.get("Mailadresse"))
                        ):
                            updated_fields.append("email")
                        if _update_if_diff(
                            m, "phone_number", _normalize_cell(row.get("Telefon"))
                        ):
                            updated_fields.append("phone_number")
                        if _update_if_diff(
                            m,
                            "phone_number_landline",
                            _normalize_cell(row.get("Telefon 2")),
                        ):
                            updated_fields.append("phone_number_landline")
                        if _update_if_diff(m, "iban", _normalize_cell(row.get("IBAN"))):
                            updated_fields.append("iban")
                        if _update_if_diff(
                            m, "account_owner", _normalize_cell(row.get("Kontoinhaber"))
                        ):
                            updated_fields.append("account_owner")
                        if _update_if_diff(
                            m, "sepa_consent", _to_datetime(row.get("consent_sepa"))
                        ):
                            updated_fields.append("sepa_consent")
                        if _update_if_diff(
                            m,
                            "privacy_consent",
                            _to_datetime(row.get("privacy_consent")),
                        ):
                            updated_fields.append("privacy_consent")

                        # Handle MemberPickupLocation update
                        mp = MemberPickupLocation.objects.filter(member=m).first()
                        mp_updated = False
                        if mp:
                            if _update_if_diff(mp, "pickup_location", picloc):
                                mp_updated = True
                            if _update_if_diff(
                                mp, "valid_from", _to_date(row.get("AO_gueltig_ab"))
                            ):
                                mp_updated = True
                        elif picloc:
                            mp = MemberPickupLocation(
                                member=m,
                                pickup_location=picloc,
                                valid_from=_to_date(row.get("AO_gueltig_ab")),
                            )
                            mp_updated = True

                        soli_val = _safe_float(row.get("Absoluter Betrag"))
                        soli_start_date = _to_date(row.get("Startdatum"))
                        soli_end_date = _to_date(row.get("Endedatum"))

                        # SolidarityContribution update
                        soli_contribution = SolidarityContribution.objects.filter(
                            member=m
                        ).first()
                        soli_updated = False
                        if soli_contribution:
                            if soli_val > 0:
                                if _update_if_diff(
                                    soli_contribution, "amount", soli_val
                                ):
                                    soli_updated = True
                                if (
                                    _update_if_diff(
                                        soli_contribution, "start_date", soli_start_date
                                    )
                                    and soli_start_date
                                ):
                                    soli_updated = True
                                if (
                                    _update_if_diff(
                                        soli_contribution, "end_date", soli_end_date
                                    )
                                    and soli_end_date
                                ):
                                    soli_updated = True
                            else:
                                # If amount is 0, we should probably delete it or leave it?
                                # Requirement: "Wenn der Solidarbetrag 0€ oder leer ist, soll kein entsprechendes Objekt erstellt werden."
                                # For update, maybe delete if it exists? The requirement is about creation.
                                # Let's stick to update only if soli_val > 0.
                                pass
                        elif soli_val > 0:
                            soli_contribution = SolidarityContribution(
                                member=m,
                                amount=soli_val,
                                start_date=soli_start_date
                                or (
                                    m.created_at.date() if m.created_at else get_today()
                                ),
                                end_date=soli_end_date
                                or GrowingPeriod.objects.filter(
                                    start_date__lte=get_today()
                                )
                                .order_by("-start_date")
                                .first()
                                .end_date,
                            )
                            soli_updated = True

                        try:
                            if not dry_run:
                                with transaction.atomic():
                                    if updated_fields:
                                        m.save(bypass_keycloak=True)
                                    if mp_updated:
                                        mp.save()
                                    if soli_updated:
                                        soli_contribution.save()

                            if updated_fields or mp_updated or soli_updated:
                                updated += 1
                            else:
                                skipped += 1
                        except Exception as e:
                            self.stderr.write(f"Error updating member {member_no}: {e}")
                            skipped += 1
                        continue

                    # If member doesn't exist, create it
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
                        member_no=member_no,
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
                    soli_val = _safe_float(row.get("Absoluter Betrag"))
                    soli_start_date = _to_date(row.get("Startdatum"))
                    soli_end_date = _to_date(row.get("Endedatum"))

                    # Persists member and pickup location transactionally; handles errors
                    try:
                        if dry_run:
                            created += 1
                        else:
                            with transaction.atomic():
                                m.save(bypass_keycloak=True)
                                MemberImportedLogEntry().populate(
                                    actor=None, user=m, model=m
                                ).save()
                                if picloc is not None:
                                    mp.save()
                                if soli_val > 0:
                                    # Create solidarity contribution if present
                                    SolidarityContribution.objects.create(
                                        member=m,
                                        amount=soli_val,
                                        start_date=soli_start_date
                                        or (
                                            m.created_at.date()
                                            if m.created_at
                                            else get_today()
                                        ),
                                        end_date=soli_end_date
                                        or GrowingPeriod.objects.filter(
                                            start_date__lte=get_today()
                                        )
                                        .order_by("-start_date")
                                        .first()
                                        .end_date,  # Fallback logic for end date
                                    )
                            created += 1
                    except Exception as e:
                        self.stderr.write(str(e))
                        skipped += 1
                        continue
            if import_type == "shares":
                if delete_all:
                    TransferCoopSharesLogEntry.objects.all().delete()
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

                    timestamp = _to_datetime_from_date(
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
                    SolidarityContribution.objects.all().delete()
                    SubscriptionChangeLogEntry.objects.all().delete()
                    Subscription.objects.all().delete()
                    Payment.objects.all().delete()
                # for row in reader:
                for row in reader:
                    if not any(_normalize_cell(v) for v in row.values()):
                        continue
                    # VertragNr,Zeitstempel,E-Mail-Adresse,Tapir-ID,Mitgliedernummer,Probevertrag,Vertragsbeginn,[S-Ernteanteil],[M-Ernteanteil],[L-Ernteanteil],[XL-Ernteanteil],product,Quantity,"Gesamtzahlung",Vertragsgrundsätze,Abholort,Email-Adressen,Ernteanteilsreduzierung/erhöhung,consent_widerruf,consent_vertragsgrundsätze,cancellation.ts
                    # print(row)
                    # identify MemberID, either via MemberNo or Email
                    try:
                        start_date = _to_date(row.get("Vertragsbeginn"))
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

                        if _normalize_cell(row.get("Mitgliedernummer")) != "":
                            member_no = _normalize_cell(row.get("Mitgliedernummer"))
                            try:
                                m = Member.objects.get(member_no=int(member_no))
                            except ValueError:
                                self.stderr.write(str(row))
                                self.stderr.write(
                                    f"Invalid member number: {member_no}. Skipping row."
                                )
                                continue
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

                    quantity = _safe_float(row.get("Quantity"))
                    v_start_date = _to_date(row.get("Vertragsbeginn"))
                    v_end_date = _to_date(row.get("Vertragsende"))
                    consent_ts = _to_datetime(
                        row.get("consent_vertragsgrundsätze")
                    ) or _to_datetime_from_date(row.get("consent_vertragsgrundsätze"))
                    withdrawal_consent_ts = _to_datetime(
                        row.get("consent_widerruf")
                    ) or _to_datetime_from_date(row.get("consent_widerruf"))

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
                        if trial_disabled_val is not None:
                            if _update_if_diff(
                                existing_sub, "trial_disabled", trial_disabled_val
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
                                        trial_disabled_val
                                        if trial_disabled_val is not None
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
