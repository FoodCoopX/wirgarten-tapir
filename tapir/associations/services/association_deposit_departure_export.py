import datetime

from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.utils.services.tapir_cache import TapirCache

from django.db.models import Exists, OuterRef, Q, QuerySet

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_annotator import (
    AssociationDepositAnnotator,
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
            get_queryset=cls.get_memberships,
            get_available_columns=cls.get_columns,
            is_available=association_deposits_enabled,
        )

    @staticmethod
    def get_memberships(
        reference_datetime: datetime.datetime,
    ) -> QuerySet[AssociationMembership]:
        cache = {}
        if not association_deposits_enabled(cache=cache):
            return AssociationMembership.objects.none()
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
            return AssociationMembership.objects.none()
        memberships = (
            AssociationMembership.objects.filter(
                end_date__gte=growing_period.start_date,
                end_date__lte=growing_period.end_date,
                end_date__lt=get_today(cache=cache),
            )
            .filter(
                ~Exists(
                    AssociationMembership.objects.filter(
                        member_id=OuterRef("member_id")
                    ).filter(
                        Q(start_date__gt=OuterRef("start_date"))
                        | Q(start_date=OuterRef("start_date"), pk__gt=OuterRef("pk"))
                    )
                )
            )
            .select_related("member")
        )
        return (
            AssociationDepositAnnotator.annotate_memberships(memberships)
            .filter(deposit_exported__gt=0)
            .order_by("member__member_no", "end_date", "pk")
        )

    @classmethod
    def get_columns(cls) -> list[ExportSegmentColumn]:
        return [
            ExportSegmentColumn(
                "member",
                "Mitglied",
                "",
                lambda membership, _, __: membership.member.get_display_name(),
            ),
            ExportSegmentColumn(
                "departure",
                "Austritt",
                "",
                lambda membership, _, __: membership.end_date.isoformat(),
            ),
            ExportSegmentColumn(
                "account_owner",
                "Kontoinhaber",
                "",
                lambda membership, _, __: membership.member.account_owner,
            ),
            ExportSegmentColumn(
                "iban",
                "IBAN",
                "",
                lambda membership, _, __: membership.member.iban,
            ),
            ExportSegmentColumn(
                "amount",
                "Einlage (€)",
                "",
                lambda membership, _, __: format_currency(membership.deposit_exported),
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
