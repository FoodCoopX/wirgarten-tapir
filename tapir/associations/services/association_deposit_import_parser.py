from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator, MinValueValidator

from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.utils import get_now, get_today


class AssociationDepositImportParser:
    AMOUNT_COLUMN = "Einlage Gesamt"
    EFFECTIVE_FROM_COLUMN = "Einlage Beginn"
    REQUESTED_AT_COLUMN = "Einlage Anfrage"

    COLUMNS = {
        "Nr",
        "Einlage Status",
        AMOUNT_COLUMN,
        "Einlage Erhalten",
        "Einlage Stichtag",
        EFFECTIVE_FROM_COLUMN,
        "Einlage Ratenzahl",
        "Einlage Offene Raten",
        "Einlage Individuell",
        REQUESTED_AT_COLUMN,
        "Einlage Beleg",
    }

    @staticmethod
    def money(value) -> Decimal:
        try:
            amount = Decimal(str(value).strip().replace(",", "."))
        except InvalidOperation:
            raise ValidationError("Ungültiger Einlagenbetrag.")
        DecimalValidator(8, 2)(amount)
        MinValueValidator(Decimal("0"))(amount)
        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def date(value):
        date = DataImportUtils.to_date(value)
        if date is None:
            raise ValidationError("Ein gültiges Einlagendatum ist erforderlich.")
        return date

    @classmethod
    def parse(cls, row: dict, cache: dict) -> dict:
        if set(row) - cls.COLUMNS:
            raise ValidationError(
                "Unbekannte Spalten im Einlagenimport; bitte das dokumentierte Format verwenden."
            )
        row = {key: DataImportUtils.normalize_cell(value) for key, value in row.items()}
        state = row.get("Einlage Status", "").strip()
        if state not in ("vereinbart", "offen"):
            raise ValidationError("Einlage Status muss vereinbart oder offen sein.")
        received = cls.money(row.get("Einlage Erhalten") or "0")
        as_of = cls.date(row.get("Einlage Stichtag"))
        if as_of > get_today(cache):
            raise ValidationError(
                "Der Einlagenstichtag darf nicht in der Zukunft liegen."
            )
        note = row.get("Einlage Beleg", "").strip()
        if not note or len(note) > 3000:
            raise ValidationError(
                "Ein Belegtext mit höchstens 3000 Zeichen ist erforderlich."
            )
        count = int(row.get("Einlage Ratenzahl") or "1")
        AssociationDepositInstalmentCalculator.validate_instalment_count(count)
        individual = (row.get("Einlage Individuell") or "nein").strip()
        if individual not in ("ja", "nein"):
            raise ValidationError("Einlage Individuell muss ja oder nein sein.")
        rates = cls._parse_open_rates(row.get("Einlage Offene Raten") or "", count)
        if state == "offen":
            amount, effective, requested = cls._parse_pending_terms(
                row, count, rates, cache
            )
        else:
            amount, effective, requested = cls._parse_agreed_terms(
                row, received, count, rates
            )
        return {
            "state": state,
            "amount": amount,
            "received": received,
            "as_of": as_of,
            "effective": effective,
            "requested": requested,
            "count": count,
            "individual": individual == "ja",
            "rates": rates,
            "note": note,
        }

    @classmethod
    def _parse_open_rates(cls, raw_rates: str, count: int) -> list[dict]:
        rates = []
        for value in raw_rates.split("|", 12):
            if not value.strip():
                continue
            if len(rates) >= count:
                raise ValidationError("Es gibt mehr offene Raten als vereinbart.")
            parts = value.strip().split(":", 1)
            if len(parts) != 2:
                raise ValidationError("Raten bitte als Datum:Betrag angeben.")
            date, amount = parts
            due, amount = cls.date(date), cls.money(amount)
            if amount == 0 or (
                rates
                and (
                    due.year * 12 + due.month
                    != rates[-1]["due_date"].year * 12 + rates[-1]["due_date"].month + 1
                )
            ):
                raise ValidationError(
                    "Offene Monatsraten müssen positiv und lückenlos aufsteigend sein."
                )
            rates.append({"due_date": due, "amount": amount})
        return rates

    @classmethod
    def _parse_pending_terms(
        cls, row: dict, count: int, rates: list[dict], cache: dict
    ):
        requested = DataImportUtils.to_datetime(row.get(cls.REQUESTED_AT_COLUMN))
        if (
            not requested
            or requested > get_now(cache)
            or row.get(cls.AMOUNT_COLUMN)
            or row.get(cls.EFFECTIVE_FROM_COLUMN)
            or rates
            or count != 1
        ):
            raise ValidationError(
                "Offene Vereinbarung benötigt ein Anfragedatum, aber keinen Gesamtbetrag, Beginn oder Ratenplan."
            )
        return None, None, requested

    @classmethod
    def _parse_agreed_terms(
        cls, row: dict, received: Decimal, count: int, rates: list[dict]
    ):
        amount = cls.money(row.get(cls.AMOUNT_COLUMN))
        effective = cls.date(row.get(cls.EFFECTIVE_FROM_COLUMN))
        if (amount == 0 and count != 1) or any(
            rate["due_date"] < effective for rate in rates
        ):
            raise ValidationError(
                "Raten dürfen nicht vor dem vereinbarten Beginn liegen; ein Verzicht benötigt Ratenzahl 1."
            )
        if sum((r["amount"] for r in rates), Decimal("0")) != max(
            Decimal("0"), amount - received
        ):
            raise ValidationError(
                "Erhaltene Beträge und tatsächlich offene Raten passen nicht zum vereinbarten Gesamtbetrag."
            )
        if row.get(cls.REQUESTED_AT_COLUMN):
            raise ValidationError(
                "Ein vereinbarter Importstand ist keine ungeklärte Anfrage."
            )
        return amount, effective, None
