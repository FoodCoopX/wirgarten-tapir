from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from django.db import transaction
from django.db.models import Q

from tapir.associations.models import (
    AssociationDepositTransaction,
    AssociationMembership,
    AssociationMembershipUpdatedLogEntry,
)
from tapir.log.models import TextLogEntry
from tapir.log.util import freeze_for_log
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import (
    format_currency,
    get_now,
    get_today,
    legal_status_is_association,
)


class AssociationDepositImporter:
    @classmethod
    @transaction.atomic
    def import_deposit(cls, row: dict[str, str], cache: dict) -> str | None:
        if DataImportUtils.is_row_empty(row):
            return None
        if not legal_status_is_association(cache=cache):
            raise ValidationError(
                "Vereinseinlagen können nur für Vereine importiert werden."
            )
        unknown_columns = set(row) - {
            "Nr",
            "Einlage Erhalten",
            "Einlage Offen",
            "Einlage Status",
        }
        if unknown_columns:
            raise ValidationError(
                f"Unbekannte Spalten im Einlagenimport: {', '.join(sorted(unknown_columns))}."
            )
        member_number = DataImportUtils.parse_member_number(row.get("Nr"), cache=cache)
        if member_number is None:
            raise ValidationError("Eine Mitgliedsnummer ist erforderlich.")
        status = DataImportUtils.normalize_cell(row.get("Einlage Status"))
        received, outstanding = cls._parse_amounts(row, status)
        member = Member.objects.get(member_no=member_number)
        membership = (
            AssociationMembership.objects.filter(
                member=member, start_date__lte=get_today(cache=cache)
            )
            .order_by("start_date")
            .last()
        )
        if membership is None:
            raise ValidationError(
                "Für das Mitglied liegt keine Vereinsmitgliedschaft vor."
            )
        if status == "offen":
            if AssociationMembership.objects.filter(
                member=member, deposit_agreement_requested_at__isnull=False
            ).exists():
                return MEMBER_IMPORT_STATUS_SKIPPED
            previous = freeze_for_log(membership)
            membership.deposit_agreement_requested_at = get_now(cache=cache)
            membership.save(update_fields=["deposit_agreement_requested_at"])
            AssociationMembershipUpdatedLogEntry().populate(
                old_frozen=previous, new_model=membership, actor=None, user=member
            ).save()
            return MEMBER_IMPORT_STATUS_CREATED

        transactions = AssociationDepositTransaction.objects.filter(member=member)
        historical = transactions.filter(
            Q(transaction_type=AssociationDepositTransaction.Type.IMPORT)
            | Q(
                transaction_type=AssociationDepositTransaction.Type.SUBSCRIPTION,
                payments__isnull=True,
            )
        )
        expected = []
        if received:
            expected.append((AssociationDepositTransaction.Type.IMPORT, received))
        if outstanding:
            expected.append(
                (AssociationDepositTransaction.Type.SUBSCRIPTION, outstanding)
            )
        if transactions.exists():
            if sorted(historical.values_list("transaction_type", "amount")) == sorted(
                expected
            ):
                return MEMBER_IMPORT_STATUS_SKIPPED
            raise ValidationError(
                "Für dieses Mitglied bestehen bereits abweichende Einlagenbuchungen."
            )
        for transaction_type, amount in expected:
            AssociationDepositTransaction.objects.create(
                member=member,
                transaction_type=transaction_type,
                amount=amount,
                valid_at=get_today(cache=cache),
            )
        TextLogEntry().populate(
            user=member,
            actor=None,
            text=f"Vereinseinlage importiert: erhalten {format_currency(received)} €, offen {format_currency(outstanding)} €.",
        ).save()
        return MEMBER_IMPORT_STATUS_CREATED

    @staticmethod
    def _parse_amounts(row: dict[str, str], status: str) -> tuple[Decimal, Decimal]:
        if status not in ("", "vereinbart", "offen"):
            raise ValidationError("Einlage Status muss vereinbart oder offen sein.")
        received = DataImportUtils.parse_amount(row, "Einlage Erhalten")
        outstanding = DataImportUtils.parse_amount(row, "Einlage Offen")
        if status == "offen" and (received or outstanding):
            raise ValidationError(
                "Eine offene Vereinbarung darf keinen Einlagenbetrag enthalten."
            )
        if status != "offen" and received + outstanding <= 0:
            raise ValidationError(
                "Ein erhaltener oder offener Betrag ist erforderlich."
            )
        DecimalValidator(8, 2)(received + outstanding)
        return received, outstanding
