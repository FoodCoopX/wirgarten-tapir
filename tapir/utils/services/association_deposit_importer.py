from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.associations.models import AssociationDepositOperation
from tapir.associations.services.association_deposit_service import (
    AssociationDepositService,
)
from tapir.associations.services.deposit_configuration import DepositConfiguration
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.models import Member


class AssociationDepositImporter:
    @classmethod
    @transaction.atomic
    def import_opening_balance(cls, row: dict, cache: dict):
        if DataImportUtils.is_row_empty(row):
            return None
        reference = DataImportUtils.normalize_cell(row.get("Buchungs-ID"))
        if not reference or len(reference) > 80:
            raise ValidationError(
                "Eine dauerhafte Buchungs-ID (höchstens 80 Zeichen) ist erforderlich."
            )
        member_no = DataImportUtils.normalize_cell(row.get("Mitgliedsnummer"))
        try:
            member = Member.objects.select_for_update().get(member_no=member_no)
        except (Member.DoesNotExist, ValueError, TypeError):
            raise ValidationError(
                "Mitgliedsnummer nicht gefunden. Bitte zuerst die Mitglieder mit stabilen Mitgliedsnummern importieren."
            )
        request_id = "import:" + reference
        previous = AssociationDepositOperation.objects.filter(
            request_id=request_id
        ).first()
        if previous and previous.deposit.member_id != member.pk:
            raise ValidationError(
                "Diese Buchungs-ID gehört bereits zu einem anderen Mitglied."
            )
        amount = DepositConfiguration.money(
            DataImportUtils.normalize_cell(row.get("Betrag")).replace(",", ".")
        )
        date = cls.date(row.get("Datum"), "Datum")
        if amount and date is None:
            raise ValidationError(
                "Das Datum des bereits erhaltenen Anfangsbestands ist erforderlich."
            )
        cancellation_date = cls.date(row.get("Austrittsdatum"), "Austrittsdatum")
        data = {
            "action": "import",
            "amount": str(amount),
            "date": date,
            "cancellation_date": cancellation_date,
            "note": "Historischer, bereits erhaltener Anfangsbestand; Beleg: "
            + reference,
        }
        state = DataImportUtils.normalize_cell(row.get("Status")).lower()
        if state not in {"", "bezahlt", "vereinbart", "haertefall"}:
            raise ValidationError(
                "Status muss bezahlt, vereinbart oder haertefall sein."
            )
        if state in {"vereinbart", "haertefall"}:
            total = DataImportUtils.normalize_cell(row.get("Gesamtbetrag"))
            data.update(
                agreed_amount=(
                    str(DepositConfiguration.money(total.replace(",", ".")))
                    if total
                    else None
                ),
                hardship_pending=state == "haertefall",
                agreement_note=DataImportUtils.normalize_cell(row.get("Vereinbarung")),
                open_instalments=cls.schedule(row.get("Offene Raten")),
                note="Importierter Einlagenstand; Beleg: " + reference,
            )
        elif any(
            DataImportUtils.is_cell_filled(row, field)
            for field in ["Gesamtbetrag", "Offene Raten", "Vereinbarung"]
        ):
            raise ValidationError(
                "Für einen vereinbarten Gesamtbetrag oder Ratenplan bitte Status vereinbart angeben."
            )
        elif not amount:
            raise ValidationError("Für Status bezahlt muss der Betrag positiv sein.")
        AssociationDepositService.apply(
            member=member,
            actor=None,
            cache=cache,
            administrative=True,
            request_id=request_id,
            data=data,
        )
        return (
            MEMBER_IMPORT_STATUS_SKIPPED if previous else MEMBER_IMPORT_STATUS_CREATED
        )

    @staticmethod
    def date(value, label):
        if not DataImportUtils.normalize_cell(value):
            return None
        try:
            parsed = DataImportUtils.to_date(value)
        except ValueError:
            parsed = None
        if parsed is None:
            raise ValidationError(
                f"Ungültiges Datum in {label}; bitte JJJJ-MM-TT verwenden."
            )
        return parsed

    @classmethod
    def schedule(cls, value):
        value = DataImportUtils.normalize_cell(value)
        if not value:
            return []
        result = []
        for entry in value.split("|"):
            parts = entry.strip().split(":")
            if len(parts) != 2:
                raise ValidationError(
                    "Offene Raten bitte als JJJJ-MM-TT:Betrag|JJJJ-MM-TT:Betrag angeben."
                )
            result.append(
                {
                    "due_date": cls.date(parts[0], "Offene Raten"),
                    "amount": str(
                        DepositConfiguration.money(parts[1].strip().replace(",", "."))
                    ),
                }
            )
        return result
