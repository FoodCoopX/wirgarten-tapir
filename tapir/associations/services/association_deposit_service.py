import datetime
import json
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Sum

from tapir.associations.models import (
    AssociationDeposit,
    AssociationDepositBooking,
    AssociationDepositLogEntry,
    AssociationDepositOperation,
    AssociationMembership,
)
from tapir.associations.services.deposit_configuration import DepositConfiguration
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import format_currency, get_today


class AssociationDepositService:
    @classmethod
    def validate_signup(
        cls, amount, hardship: bool, has_products: bool, cache: dict, instalments=False
    ):
        config = DepositConfiguration.get(cache)
        if instalments and (
            not config["enabled"] or not config["instalments_enabled"] or hardship
        ):
            raise ValidationError(
                "Standardraten sind für diese Anmeldung nicht verfügbar."
            )
        amount = DepositConfiguration.money(amount or 0)
        if not config["enabled"]:
            if amount or hardship:
                raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
            return
        if hardship:
            if not config["allow_hardship"] or amount:
                raise ValidationError(
                    "Härtefall nur ohne Einzug und bei aktivierter Härtefallregelung möglich."
                )
            return
        if not has_products and not config["supporters_required"] and amount == 0:
            return
        cls.validate_regular_amount(amount, config)
        if not config["allow_extra_signup"] and amount != config["minimum"]:
            raise ValidationError(
                "Bei der Anmeldung ist nur die Mindesteinlage erlaubt."
            )

    @staticmethod
    def validate_regular_amount(amount: Decimal, config: dict):
        minimum = DepositConfiguration.money(config["minimum"])
        increment = DepositConfiguration.money(config["increment"])
        if minimum <= 0 or increment <= 0:
            raise ValidationError("Mindestbetrag und Schrittgröße müssen positiv sein.")
        if amount < minimum:
            raise ValidationError(
                f"Die Mindesteinlage beträgt {format_currency(minimum)} €."
            )
        if (amount - minimum) % increment:
            raise ValidationError(
                f"Bitte Schritte von {format_currency(increment)} € ab der Mindesteinlage verwenden."
            )

    @classmethod
    def register(
        cls,
        member,
        amount,
        hardship,
        has_products,
        effective_from,
        actor,
        cache,
        instalments=False,
    ):
        cls.validate_signup(amount, hardship, has_products, cache, instalments)
        if not DepositConfiguration.get(cache)["enabled"]:
            return None
        return cls.apply(
            member=member,
            actor=actor,
            cache=cache,
            request_id="registration",
            data={
                "action": "hardship" if hardship else "registration",
                "amount": str(amount or 0),
                "start_date": effective_from,
                "instalments": (
                    DepositConfiguration.get(cache)["instalment_count"]
                    if instalments
                    else 1
                ),
            },
            administrative=False,
        )

    @classmethod
    def balances(cls, deposit: AssociationDeposit, cache: dict, reference_date=None):
        reference_date = reference_date or get_today(cache=cache)
        collected = deposit.payments.filter(
            status=Payment.PaymentStatus.PAID, due_date__lte=reference_date
        ).aggregate(total=Sum("amount"))["total"] or Decimal(0)
        totals = {
            row["kind"]: row["total"]
            for row in deposit.bookings.filter(date__lte=reference_date)
            .values("kind")
            .annotate(total=Sum("amount"))
        }
        received = (
            collected
            + totals.get("receipt", 0)
            + totals.get("import", 0)
            - totals.get("reversal", 0)
        )
        refunded = totals.get("refund", Decimal(0))
        balance = received - refunded
        pending = deposit.payments.filter(
            transaction=None, status=Payment.PaymentStatus.DUE
        ).aggregate(total=Sum("amount"))["total"] or Decimal(0)
        # Exported payments are immutable even before their collection date.
        committed = deposit.payments.filter(
            status=Payment.PaymentStatus.PAID
        ).aggregate(total=Sum("amount"))["total"] or Decimal(0)
        committed += sum(
            deposit.bookings.filter(kind__in=["receipt", "import"]).values_list(
                "amount", flat=True
            ),
            Decimal(0),
        )
        committed -= sum(
            deposit.bookings.filter(kind__in=["reversal", "refund"]).values_list(
                "amount", flat=True
            ),
            Decimal(0),
        )
        ended = (
            deposit.cancellation_date is not None
            and deposit.cancellation_date <= reference_date
        )
        refundable = max(
            Decimal(0),
            (
                balance
                if ended
                else (
                    balance - deposit.agreed_amount
                    if deposit.agreed_amount is not None
                    else 0
                )
            ),
        )
        return {
            "received": received,
            "refunded": refunded,
            "balance": balance,
            "pending": pending,
            "committed": committed,
            "refundable": refundable,
        }

    @classmethod
    def snapshot(cls, deposit, cache):
        return {
            "agreed_amount": deposit.agreed_amount,
            "minimum_at_agreement": deposit.minimum_at_agreement,
            "effective_from": deposit.effective_from,
            "hardship_pending": deposit.hardship_pending,
            "exception_authorized": deposit.exception_authorized,
            "cancellation_date": deposit.cancellation_date,
            "payments": list(
                deposit.payments.order_by("due_date", "id").values(
                    "id", "amount", "due_date", "status", "transaction_id"
                )
            ),
            **cls.balances(deposit, cache),
        }

    @classmethod
    @transaction.atomic
    def apply(
        cls,
        member: Member,
        data: dict,
        request_id: str,
        actor,
        cache: dict,
        administrative: bool,
        expected_revision=None,
    ):
        Member.objects.select_for_update().get(pk=member.pk)
        deposit, _ = AssociationDeposit.objects.get_or_create(member=member)
        deposit = AssociationDeposit.objects.select_for_update().get(pk=deposit.pk)
        payload = json.loads(
            json.dumps(
                {
                    "data": data,
                    "actor_id": actor.pk if actor else None,
                    "administrative": administrative,
                },
                cls=DjangoJSONEncoder,
            )
        )
        previous = deposit.operations.filter(request_id=request_id).first()
        if previous:
            if previous.payload != payload:
                raise ValidationError(
                    "Diese Vorgangsnummer wurde bereits für andere Angaben verwendet."
                )
            return deposit
        if expected_revision is not None and deposit.revision != expected_revision:
            raise ValidationError(
                "Die Einlage wurde inzwischen geändert. Bitte neu laden."
            )

        action = data["action"]
        if action not in {
            "registration",
            "increase",
            "agreement",
            "hardship",
            "receipt",
            "refund",
            "reversal",
            "import",
            "cancel",
            "rejoin",
        }:
            raise ValidationError("Unbekannter Einlagenvorgang.")
        if not administrative and action not in {
            "registration",
            "increase",
            "hardship",
        }:
            raise ValidationError("Dieser Vorgang ist nur für die Verwaltung erlaubt.")
        config = DepositConfiguration.get(cache)
        if not config["enabled"] and action in {
            "registration",
            "increase",
            "hardship",
            "agreement",
        }:
            raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
        note = data.get("note", "").strip()
        if administrative and action not in {"cancel", "rejoin"} and not note:
            raise ValidationError(
                "Bitte die Vereinbarung oder den Buchungsgrund angeben."
            )
        before = cls.snapshot(deposit, cache)
        operation = AssociationDepositOperation.objects.create(
            deposit=deposit, request_id=request_id, payload=payload, actor=actor
        )

        if action == "hardship":
            if (
                not config["allow_hardship"]
                or deposit.agreed_amount is not None
                or deposit.payments.exists()
                or deposit.bookings.exists()
            ):
                raise ValidationError(
                    "Eine bestehende Einlagenvereinbarung kann nicht durch eine Härtefallanfrage aufgehoben werden."
                )
            deposit.hardship_pending = True
            description = (
                "Härtefall angefragt; keine Einlagenvereinbarung und kein Einzug."
            )
        elif action in {"registration", "increase", "agreement"}:
            if deposit.cancellation_date:
                raise ValidationError(
                    "Für eine gekündigte Einlage ist keine neue Lastschrift möglich. Bitte die Rückzahlung zuerst mit der Verwaltung klären."
                )
            amount = DepositConfiguration.money(data["amount"])
            count = data.get("instalments", 1)
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or not 1 <= count <= 120
            ):
                raise ValidationError("Die Ratenzahl muss zwischen 1 und 120 liegen.")
            if action == "increase":
                if (
                    not config["allow_extra_member"]
                    or deposit.hardship_pending
                    or deposit.agreed_amount is None
                ):
                    raise ValidationError(
                        "Eine Erhöhung ist derzeit nicht möglich. Bitte die Verwaltung kontaktieren."
                    )
                if amount <= deposit.agreed_amount or count != 1:
                    raise ValidationError(
                        "Bitte einen höheren Gesamtbetrag wählen. Raten brauchen eine Vereinbarung mit der Verwaltung."
                    )
                cls.validate_regular_amount(amount, config)
                if (
                    not AssociationMembership.objects.filter(member=member)
                    .filter(end_date__isnull=True)
                    .exists()
                    and not AssociationMembership.objects.filter(
                        member=member, end_date__gte=get_today(cache)
                    ).exists()
                ):
                    raise ValidationError(
                        "Keine laufende oder zukünftige Vereinsmitgliedschaft vorhanden."
                    )
            elif action == "registration":
                if (
                    deposit.agreed_amount is not None
                    or deposit.payments.exists()
                    or deposit.bookings.exists()
                ):
                    raise ValidationError(
                        "Für dieses Mitglied besteht bereits eine Einlage."
                    )
            else:
                deposit.exception_authorized = True
            first_date = data.get("start_date") or get_today(cache)
            if isinstance(first_date, str):
                first_date = datetime.date.fromisoformat(first_date)
            if first_date < get_today(cache):
                raise ValidationError(
                    "Neue Lastschriften dürfen nicht rückdatiert werden."
                )
            old_amount = deposit.agreed_amount or Decimal(0)
            deposit.agreed_amount = amount
            deposit.minimum_at_agreement = config["minimum"]
            deposit.effective_from = deposit.effective_from or first_date
            deposit.hardship_pending = False
            if action == "increase":
                balances = cls.balances(deposit, cache)
                extra = min(
                    amount - old_amount,
                    max(
                        Decimal(0), amount - balances["committed"] - balances["pending"]
                    ),
                )
                cls.create_payments(deposit, extra, 1, first_date, cache)
            else:
                cls.delete_open_payments(deposit)
                remaining = max(
                    Decimal(0), amount - cls.balances(deposit, cache)["committed"]
                )
                cls.create_payments(deposit, remaining, count, first_date, cache)
            description = f"Gesamteinlage vereinbart: {format_currency(amount)} €; {count} Rate(n). {note}"
        elif action == "import":
            description = cls.import_opening_state(
                deposit, operation, data, note, cache
            )
        elif action == "rejoin":
            membership = AssociationMembership.objects.get(
                pk=data["membership_id"], member=member
            )
            if (
                deposit.cancellation_date is None
                or membership.start_date < deposit.cancellation_date
            ):
                raise ValidationError("Kein Wiedereintritt nach Kündigung der Einlage.")
            deposit.cancellation_date = None
            deposit.agreed_amount = None
            deposit.minimum_at_agreement = None
            deposit.effective_from = membership.start_date
            deposit.exception_authorized = False
            deposit.hardship_pending = False
            description = (
                "Wiedereintritt; individuelle Einlagenvereinbarung offen. "
                "Guthaben und Buchungshistorie bleiben erhalten; kein neuer Einzug."
            )
        elif action == "cancel":
            date = data["date"]
            if isinstance(date, str):
                date = datetime.date.fromisoformat(date)
            deposit.cancellation_date = date
            cls.delete_open_payments(deposit)
            description = f"Einlage zum {date:%d.%m.%Y} gekündigt; offene Einzüge aufgehoben. Rückzahlung erfolgt außerhalb von Tapir."
        else:
            amount = DepositConfiguration.money(data["amount"])
            if not amount:
                raise ValidationError("Der Buchungsbetrag muss positiv sein.")
            date = data.get("date") or get_today(cache)
            if isinstance(date, str):
                date = datetime.date.fromisoformat(date)
            if date > get_today(cache):
                raise ValidationError(
                    "Erhaltene oder zurückgezahlte Beträge dürfen nicht in der Zukunft liegen."
                )
            balances = cls.balances(deposit, cache)
            dated_balances = cls.balances(deposit, cache, date)
            if action == "refund" and amount > min(
                balances["refundable"], dated_balances["refundable"]
            ):
                raise ValidationError(
                    "Die Rückzahlung übersteigt den verfügbaren Rückzahlungsbetrag."
                )
            if action == "reversal" and amount > min(
                balances["received"], dated_balances["received"]
            ):
                raise ValidationError(
                    "Die Korrektur übersteigt die erfassten Zahlungseingänge."
                )
            AssociationDepositBooking.objects.create(
                deposit=deposit,
                operation=operation,
                kind=action,
                amount=amount,
                date=date,
                note=note,
            )
            if action == "receipt":
                cls.reduce_open_payments(deposit, amount)
            description = f"{AssociationDepositBooking.Kind(action).label}: {format_currency(amount)} € am {date:%d.%m.%Y}. {note}"

        deposit.revision += 1
        deposit.save()
        operation.changes = json.loads(
            json.dumps(
                {"before": before, "after": cls.snapshot(deposit, cache)},
                cls=DjangoJSONEncoder,
            )
        )
        operation.save(update_fields=["changes"])
        log = AssociationDepositLogEntry(
            operation=operation, description=f"{config['name']}: {description}"
        )
        log.populate(actor=actor, user=member).save()
        if action in {"hardship", "rejoin"}:
            from tapir.associations.services.deposit_mail_service import (
                DepositMailService,
            )

            transaction.on_commit(
                lambda: DepositMailService.notify_pending_agreement(member, cache),
                robust=True,
            )
        return deposit

    @classmethod
    def import_opening_state(cls, deposit, operation, data, note, cache: dict):
        if (
            deposit.revision
            or deposit.payments.exists()
            or deposit.bookings.exists()
            or deposit.agreed_amount is not None
            or deposit.hardship_pending
        ):
            raise ValidationError(
                "Für dieses Mitglied besteht bereits eine Einlage oder ein offener Fall. "
                "Ein zweiter Anfangsbestand ist nicht möglich; bitte eine dokumentierte Korrektur verwenden."
            )
        paid = DepositConfiguration.money(data["amount"])
        hardship = data.get("hardship_pending", False)
        agreed = data.get("agreed_amount", paid)
        agreed = DepositConfiguration.money(agreed) if agreed is not None else None
        schedule = data.get("open_instalments", [])
        date = data.get("date")
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        if paid and (date is None or date > get_today(cache)):
            raise ValidationError(
                "Für bezahlte Einlagen ist ein Eingangsdatum bis heute erforderlich."
            )
        if not paid and date is not None:
            raise ValidationError("Ohne Zahlungseingang bleibt das Eingangsdatum leer.")
        cancellation = data.get("cancellation_date")
        if isinstance(cancellation, str):
            cancellation = datetime.date.fromisoformat(cancellation)
        if cancellation and date and cancellation < date:
            raise ValidationError(
                "Das Austrittsdatum darf nicht vor dem Einzahlungsdatum liegen."
            )
        if hardship:
            if paid or agreed is not None or schedule or cancellation:
                raise ValidationError(
                    "Ein ungeklärter Härtefall hat keinen vereinbarten Betrag, Zahlungseingang, Ratenplan oder Austritt."
                )
        elif agreed is None or len(schedule) > 120:
            raise ValidationError(
                "Gesamtbetrag und höchstens 120 offene Raten sind erforderlich."
            )
        if schedule and cancellation:
            raise ValidationError(
                "Nach Kündigung dürfen keine offenen Einzüge importiert werden."
            )
        if (
            "agreed_amount" in data
            and not hardship
            and not data.get("agreement_note", "").strip()
        ):
            raise ValidationError(
                "Bitte den Beleg der bestehenden Einlagenvereinbarung angeben."
            )
        payments = []
        for entry in schedule:
            amount = DepositConfiguration.money(entry["amount"])
            due = entry["due_date"]
            if isinstance(due, str):
                due = datetime.date.fromisoformat(due)
            if not amount or due is None:
                raise ValidationError(
                    "Jede offene Rate benötigt einen positiven Betrag und ein Fälligkeitsdatum."
                )
            if payments and due <= payments[-1].due_date:
                raise ValidationError(
                    "Offene Raten müssen nach Fälligkeit aufsteigend und ohne doppelte Termine angegeben sein."
                )
            payments.append(
                Payment(
                    association_deposit=deposit,
                    type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
                    amount=amount,
                    due_date=due,
                    instalment_number=len(payments) + 1 if len(schedule) > 1 else None,
                )
            )
        if (
            not hardship
            and paid + sum((p.amount for p in payments), Decimal(0)) != agreed
        ):
            raise ValidationError(
                "Bereits bezahlt plus offene Raten muss genau dem vereinbarten Gesamtbetrag entsprechen."
            )
        if payments:
            mandate = cls.payment_mandate(deposit, cache)
            for payment in payments:
                payment.mandate_ref = mandate
            Payment.objects.bulk_create(payments)
        if paid:
            AssociationDepositBooking.objects.create(
                deposit=deposit,
                operation=operation,
                kind="import",
                amount=paid,
                date=date,
                note=note,
            )
        deposit.agreed_amount = agreed
        deposit.hardship_pending = hardship
        deposit.exception_authorized = bool(data.get("agreement_note")) and not hardship
        deposit.minimum_at_agreement = (
            None if hardship else DepositConfiguration.get(cache)["minimum"]
        )
        deposit.effective_from = date or (payments[0].due_date if payments else None)
        deposit.cancellation_date = cancellation
        return (
            f"Anfangsbestand importiert: {format_currency(paid)} € bereits bezahlt; "
            f"{len(payments)} offene Rate(n). "
            + ("Individuelle Vereinbarung offen; kein Einzug. " if hardship else "")
            + note
            + " "
            + data.get("agreement_note", "")
        )

    @staticmethod
    def delete_open_payments(deposit):
        deposit.payments.filter(
            transaction=None, status=Payment.PaymentStatus.DUE
        ).delete()

    @staticmethod
    def reduce_open_payments(deposit, amount):
        for payment in deposit.payments.filter(
            transaction=None, status=Payment.PaymentStatus.DUE
        ).order_by("due_date", "id"):
            reduction = min(payment.amount, amount)
            amount -= reduction
            payment.amount -= reduction
            if payment.amount == 0:
                payment.delete()
            elif reduction:
                payment.save(update_fields=["amount"])
            if not amount:
                break

    @classmethod
    def payment_mandate(cls, deposit, cache: dict):
        if (
            not deposit.member.iban
            or not deposit.member.account_owner
            or not deposit.member.sepa_consent
        ):
            raise ValidationError(
                "Für den Einzug werden Bankdaten und ein SEPA-Mandat benötigt."
            )
        return MandateReferenceProvider.get_or_create_mandate_reference(
            member=deposit.member, cache=cache
        )

    @classmethod
    def create_payments(cls, deposit, amount, count, first_date, cache):
        if not amount:
            return
        mandate = cls.payment_mandate(deposit, cache)
        cents = int(amount * 100)
        if count > cents:
            raise ValidationError("Jede Rate muss mindestens einen Cent betragen.")
        base, remainder = divmod(cents, count)
        first_due = CoopSharePurchaseHandler.get_payment_due_date(first_date, cache)
        Payment.objects.bulk_create(
            [
                Payment(
                    association_deposit=deposit,
                    type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
                    mandate_ref=mandate,
                    amount=Decimal(base + (index < remainder)) / 100,
                    due_date=first_due + relativedelta(months=index),
                    instalment_number=index + 1 if count > 1 else None,
                )
                for index in range(count)
            ]
        )

    @classmethod
    def rejoin_membership(cls, membership, actor, cache: dict):
        existing = AssociationDeposit.objects.filter(member=membership.member).first()
        if (
            existing is None
            or existing.cancellation_date is None
            or membership.start_date < existing.cancellation_date
        ):
            return
        cls.apply(
            member=membership.member,
            actor=actor,
            cache=cache,
            administrative=True,
            request_id=f"membership-rejoin:{membership.pk}",
            data={"action": "rejoin", "membership_id": membership.pk},
        )

    @classmethod
    def cancel_membership(cls, member, end_date, actor, cache):
        existing = AssociationDeposit.objects.filter(member=member).first()
        if existing is None or existing.cancellation_date == end_date:
            return
        cls.apply(
            member=member,
            actor=actor,
            cache=cache,
            administrative=True,
            request_id=f"membership-end:{end_date}:{existing.revision}",
            data={"action": "cancel", "date": end_date},
        )
