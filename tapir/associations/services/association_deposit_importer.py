import json

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositImportedLogEntry,
)
from tapir.associations.services.association_deposit_import_parser import (
    AssociationDepositImportParser,
)
from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import (
    format_currency,
    format_date,
    get_now,
    get_today,
    legal_status_is_association,
)


class AssociationDepositImporter:
    @staticmethod
    @transaction.atomic
    def import_deposit(row: dict, cache: dict):
        if DataImportUtils.is_row_empty(row):
            return None
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Einlagenimport ist nur für Vereine vorgesehen.")
        data = AssociationDepositImportParser.parse(row, cache)
        member = (
            Member.objects.select_for_update(no_key=True)
            .filter(member_no=int(row["Nr"]))
            .first()
        )
        if member is None:
            raise ValidationError(
                "Mitgliedsnummer unbekannt: zuerst Mitglieder importieren."
            )
        snapshot = json.dumps(data, default=str, sort_keys=True)
        previous = AssociationDepositImportedLogEntry.objects.filter(
            user=member
        ).first()
        if previous:
            if previous.values["snapshot"] == snapshot:
                return MEMBER_IMPORT_STATUS_SKIPPED
            raise ValidationError(
                "Abweichender Einlagen-Eröffnungsstand: bestehende Buchungen nicht überschreiben; bitte über die Einlagenverwaltung klären."
            )
        if AssociationDepositAccount.objects.filter(member=member).exists():
            raise ValidationError(
                "Einlagenkonto bereits vorhanden: kein Eröffnungsimport über bestehende Vorgänge."
            )
        account = AssociationDepositAccount(
            member=member,
            agreed_amount=data["amount"],
            effective_from=data["effective"],
            hardship_requested_at=data["requested"],
            instalment_count=data["count"],
            is_individual_agreement=data["individual"],
            agreement_revision=1,
        )
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        for rate in data["rates"]:
            if (
                not member.sepa_consent
                or member.sepa_consent > get_now(cache)
                or not AssociationDepositMembershipCoverage.can_collect_on(
                    account,
                    rate["due_date"],
                    max(get_today(cache), rate["due_date"]),
                    cache,
                )
            ):
                raise ValidationError(
                    "Offene Rate liegt außerhalb der vereinbarten Mitgliedschaft oder eine SEPA-Zustimmung fehlt."
                )
        account.save()
        if data["received"]:
            AssociationDepositReceiptRecorder.record_received_deposit(
                member,
                data["received"],
                data["as_of"],
                f"deposit-opening:{member.member_no}",
                data["note"],
                None,
                cache,
            )
        AssociationDepositPaymentSynchronizer.create_imported_payment_plan(
            member, account, data["rates"], cache
        )
        AssociationDepositImportedLogEntry().populate(
            frozen={
                "snapshot": snapshot,
                "source": data["note"],
                "state": data["state"],
                "as_of": format_date(data["as_of"]),
                "agreed_display": (
                    f"{format_currency(data['amount'])} €"
                    if data["amount"] is not None
                    else "Nicht vereinbart"
                ),
                "received_amount": format_currency(data["received"]),
                "open_rates": str(len(data["rates"])),
            },
            actor=None,
            user=member,
        ).save()
        return MEMBER_IMPORT_STATUS_CREATED
