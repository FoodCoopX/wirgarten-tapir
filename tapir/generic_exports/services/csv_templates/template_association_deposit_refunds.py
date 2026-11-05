import datetime

from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport, LocaleChoices
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider


class TemplateAssociationDepositRefunds:
    ID = "association_deposit_refunds"
    NAME = "Vereinseinlagen: Rückzahlungsübersicht"
    DESCRIPTION = "Jährliche Prüfliste ausgeschiedener Mitglieder mit noch gebuchtem Guthaben und Bankdaten. Keine Auszahlungsanweisung oder feste Fälligkeit; Rückzahlung nach Vereinbarung und Liquidität."

    @classmethod
    def create_exports(cls):
        if CsvExport.objects.filter(name=cls.NAME).exists():
            raise TemplateAlreadyExistsException(
                "Diese Rückzahlungsübersicht ist bereits eingerichtet."
            )
        columns = [
            "member_number",
            "member_last_name",
            "member_first_name",
            "member_email_address",
            "deposit_end",
            "deposit_balance",
            "deposit_refunded",
            "deposit_refundable",
            "member_account_owner",
            "member_iban",
            "deposit_status",
        ]
        names = {
            column.id: column.display_name
            for column in MemberColumnProvider.get_member_columns()
        }
        CsvExport.objects.create(
            name=cls.NAME,
            export_segment_id="members.association_deposit_refunds",
            file_name="Vereinseinlagen-Rueckzahlungsuebersicht.csv",
            automated_export_cycle=AutomatedExportCycle.YEARLY,
            automated_export_day=1,
            automated_export_hour=datetime.time(hour=9),
            separator=";",
            locale=LocaleChoices.DE,
            column_ids=columns,
            custom_column_names=[names[column] for column in columns],
        )
