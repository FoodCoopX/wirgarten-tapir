from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator, MinValueValidator
from django.db import transaction

from tapir.associations.models import AssociationDeposit, AssociationMembership
from tapir.associations.services.association_deposit_membership_end_handler import (
    iter_continuous_memberships,
)
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
    def import_deposit(cls, row: dict[str, str], cache: dict):
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

        member = Member.objects.select_for_update(no_key=True).get(
            member_no=member_number
        )
        membership = (
            AssociationMembership.objects.filter(
                member=member, start_date__lte=get_today(cache=cache)
            )
            .order_by("-start_date", "-pk")
            .first()
        )
        if membership is None:
            raise ValidationError(
                "Für das Mitglied liegt keine Vereinsmitgliedschaft vor."
            )
        if membership.end_date is not None:
            following_memberships = AssociationMembership.objects.filter(
                member=member, start_date__gt=membership.start_date
            ).order_by("start_date", "pk")
            for following in iter_continuous_memberships(
                following_memberships, membership.end_date
            ):
                membership = following

        previous_imports = AssociationDeposit.objects.filter(
            membership__member=member, payment=None
        ).exclude(membership=membership)
        if previous_imports.exists():
            raise ValidationError(
                "Für dieses Mitglied gibt es bereits einen historischen Einlageneintrag. "
                "Bitte die Zuordnung zur Mitgliedschaft prüfen."
            )
        existing = list(membership.deposits.all()[:2])
        if existing:
            if (
                len(existing) == 1
                and existing[0].payment_id is None
                and existing[0].opening_balance == balance
                and (existing[0].imported_outstanding_amount or Decimal("0"))
                == (unpaid or Decimal("0"))
            ):
                return MEMBER_IMPORT_STATUS_SKIPPED
            raise ValidationError(
                "Für diese Mitgliedschaft besteht bereits ein Einlageneintrag."
            )
        AssociationDeposit.objects.create(
            membership=membership,
            opening_balance=balance,
            imported_outstanding_amount=unpaid,
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
