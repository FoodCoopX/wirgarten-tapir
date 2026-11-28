import datetime

from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.utils.services.tapir_cache import TapirCache

from django.db.models import QuerySet

from tapir.associations.services.association_deposit_annotator import (
    AssociationDepositAnnotator,
)
from tapir.associations.services.association_entry_date_annotater import (
    AssociationEntryDateAnnotater,
)
from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport, LocaleChoices
from tapir.generic_exports.services.export_segment_manager import (
    ExportSegment,
    ExportSegmentColumn,
)
from tapir.wirgarten.utils import (
    format_currency,
    get_today,
)
from tapir.wirgarten.models import Member


class AssociationDepositDepartureExport:
    ID = "association_deposit_departures"
    NAME = "Vereinseinlagen ausgeschiedener Mitglieder"
    DESCRIPTION = (
        "Einlagen für Austritte in der letzten abgeschlossenen Vertragsperiode. Ein SEPA-Export bestätigt keinen Bankeingang. "
        "Bitte Zahlungseingänge vor einer Rückzahlung prüfen."
    )

    @classmethod
    def get_segment(cls) -> ExportSegment:
        return ExportSegment(
            id=cls.ID,
            display_name=cls.NAME,
            description=cls.DESCRIPTION,
            get_queryset=cls.get_members,
            get_available_columns=cls.get_columns,
            is_available=association_deposits_enabled,
        )

    @staticmethod
    def get_members(
        reference_datetime: datetime.datetime,
    ) -> QuerySet[Member]:
        cache = {}
        if not association_deposits_enabled(cache=cache):
            return Member.objects.none()
        growing_period = next(
            (
                period
                for period in reversed(
                    TapirCache.get_all_growing_periods_ascending(cache=cache)
                )
                if period.end_date < reference_datetime.date()
            ),
            None,
        )
        if growing_period is None:
            return Member.objects.none()
        members = (
            AssociationEntryDateAnnotater.annotate_queryset_with_association_exit_date(
                queryset=Member.objects.all()
            ).filter(
                association_exit_date__gte=growing_period.start_date,
                association_exit_date__lte=growing_period.end_date,
                association_exit_date__lt=get_today(cache=cache),
            )
        )
        return (
            AssociationDepositAnnotator.annotate_members(members=members)
            .filter(deposit_exported__gt=0)
            .order_by("member_no", "association_exit_date", "pk")
        )

    @classmethod
    def get_columns(cls) -> list[ExportSegmentColumn]:
        return [
            ExportSegmentColumn(
                id="member",
                display_name="Mitglied",
                description="",
                get_value=lambda member, _, __: member.get_display_name(),
            ),
            ExportSegmentColumn(
                id="departure",
                display_name="Austritt",
                description="",
                get_value=lambda member, _, __: member.association_exit_date.isoformat(),
            ),
            ExportSegmentColumn(
                id="account_owner",
                display_name="Kontoinhaber",
                description="",
                get_value=lambda member, _, __: member.account_owner,
            ),
            ExportSegmentColumn(
                id="iban",
                display_name="IBAN",
                description="",
                get_value=lambda member, _, __: member.iban,
            ),
            ExportSegmentColumn(
                id="amount",
                display_name="Einlage (€)",
                description="",
                get_value=lambda member, _, __: format_currency(
                    member.deposit_exported
                ),
            ),
        ]

    @classmethod
    def create_exports(cls) -> None:
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
