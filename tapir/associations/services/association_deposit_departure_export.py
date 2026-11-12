import datetime

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)
from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport, LocaleChoices
from tapir.generic_exports.services.export_segment_manager import (
    ExportSegment,
    ExportSegmentColumn,
)
from tapir.wirgarten.service.file_export import spreadsheet_text
from tapir.wirgarten.utils import (
    format_currency,
    get_today,
    legal_status_is_association,
)


class AssociationDepositDepartureExport:
    ID = "association_deposit_departures"
    NAME = "Vereinseinlagen ausgeschiedener Mitglieder"
    DESCRIPTION = (
        "Einlagen für Austritte im Vorjahr. Ein SEPA-Export bestätigt keinen Bankeingang. "
        "Bitte Zahlungseingänge vor einer Rückzahlung prüfen."
    )

    @classmethod
    def get_segment(cls):
        return ExportSegment(
            id=cls.ID,
            display_name=cls.NAME,
            description=cls.DESCRIPTION,
            get_queryset=cls.get_memberships,
            get_available_columns=cls.get_columns,
            requires_coop_manage=True,
        )

    @staticmethod
    def get_memberships(reference_datetime: datetime.datetime):
        cache = {}
        if not legal_status_is_association(cache=cache):
            return []
        memberships = AssociationMembership.objects.filter(
            end_date__year=reference_datetime.year - 1,
            end_date__lt=get_today(cache=cache),
        ).select_related("member")
        return (
            AssociationDepositOverviewProvider.annotate_memberships(memberships)
            .filter(deposit_exported__gt=0)
            .order_by("member__member_no", "end_date", "pk")
        )

    @staticmethod
    def get_columns():
        return [
            ExportSegmentColumn(
                "member",
                "Mitglied",
                "",
                lambda row, _, __: spreadsheet_text(row.member.get_display_name()),
            ),
            ExportSegmentColumn(
                "departure", "Austritt", "", lambda row, _, __: row.end_date.isoformat()
            ),
            ExportSegmentColumn(
                "account_owner",
                "Kontoinhaber",
                "",
                lambda row, _, __: spreadsheet_text(row.member.account_owner),
            ),
            ExportSegmentColumn(
                "iban", "IBAN", "", lambda row, _, __: spreadsheet_text(row.member.iban)
            ),
            ExportSegmentColumn(
                "amount",
                "Einlage (€)",
                "",
                lambda row, _, __: format_currency(row.deposit_exported),
            ),
        ]

    @classmethod
    def create_exports(cls):
        if CsvExport.objects.filter(name=cls.NAME).exists():
            raise TemplateAlreadyExistsException(
                f'Ein CSV-Export mit dem Namen "{cls.NAME}" existiert bereits.'
            )
        columns = cls.get_columns()
        CsvExport.objects.create(
            name=cls.NAME,
            description=cls.DESCRIPTION,
            export_segment_id=cls.ID,
            file_name="Einlagen_Austritte.csv",
            automated_export_cycle=AutomatedExportCycle.YEARLY,
            automated_export_day=1,
            automated_export_hour=datetime.time(hour=9),
            separator=";",
            locale=LocaleChoices.DE,
            column_ids=[column.id for column in columns],
            custom_column_names=[column.display_name for column in columns],
        )
