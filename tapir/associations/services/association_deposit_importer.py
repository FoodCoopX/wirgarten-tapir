from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator, MinValueValidator
from django.db import transaction

from tapir.associations.models import AssociationDeposit, AssociationMembership
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositImporter:
    @classmethod
    @transaction.atomic
    def import_deposit(cls, row: dict[str, str], cache: dict) -> str:
        if DataImportUtils.is_row_empty(row):
            return MEMBER_IMPORT_STATUS_SKIPPED
        if not legal_status_is_association(cache=cache):
            raise ValidationError(
                "Vereinseinlagen können nur für Vereine importiert werden."
            )
        member_number = DataImportUtils.safe_int(row.get("Nr"), default=None)
        if member_number is None:
            raise ValidationError("Eine Mitgliedsnummer ist erforderlich.")
        if set(row) - {"Nr", "Einlage Erhalten", "Einlage Offen", "Einlage Status"}:
            raise ValidationError("Unbekannte Spalten im Einlagenimport.")
        status = DataImportUtils.normalize_cell(row.get("Einlage Status"))
        if status not in ("", "vereinbart", "offen"):
            raise ValidationError("Einlage Status muss vereinbart oder offen sein.")
        received = cls._get_amount(row, "Einlage Erhalten")
        outstanding = cls._get_amount(row, "Einlage Offen")
        if status == "offen":
            if received or outstanding:
                raise ValidationError(
                    "Eine offene Vereinbarung darf keinen Einlagenbetrag enthalten."
                )
            balance, unpaid = None, None
        else:
            if received + outstanding <= 0:
                raise ValidationError(
                    "Ein erhaltener oder offener Betrag ist erforderlich."
                )
            DecimalValidator(8, 2)(received + outstanding)
            balance, unpaid = received, outstanding

        member = Member.objects.get(member_no=member_number)
        if not AssociationMembership.objects.filter(
            member=member, start_date__lte=get_today(cache=cache)
        ).exists():
            raise ValidationError(
                "Für das Mitglied liegt keine Vereinsmitgliedschaft vor."
            )
        deposit = AssociationDeposit.objects.filter(member=member).first()
        if deposit is not None:
            if (
                deposit.opening_balance == balance
                and deposit.imported_outstanding_amount == unpaid
                and not deposit.payments.exists()
            ):
                return MEMBER_IMPORT_STATUS_SKIPPED
            raise ValidationError(
                "Für dieses Mitglied besteht bereits ein Einlageneintrag."
            )
        AssociationDeposit.objects.create(
            member=member, opening_balance=balance, imported_outstanding_amount=unpaid
        )
        return MEMBER_IMPORT_STATUS_CREATED

    @staticmethod
    def _get_amount(row: dict[str, str], column: str) -> Decimal:
        try:
            amount = Decimal(
                DataImportUtils.normalize_cell(row.get(column)).replace(",", ".") or "0"
            )
        except InvalidOperation as error:
            raise ValidationError(f"Ungültiger Betrag in {column}.") from error
        DecimalValidator(8, 2)(amount)
        MinValueValidator(Decimal("0"))(amount)
        return amount
