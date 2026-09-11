import datetime

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.deliveries.services.joker_column_provider import JokerColumnProvider
from tapir.deliveries.services.joker_segment_provider import JokerSegmentProvider
from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport, LocaleChoices


class TemplateJokerOverview:
    ID = "joker_overview"
    NAME = "Joker Übersicht"
    DESCRIPTION = "Erzeugt eine einzige CSV-Datei mit der Liste der Joker, sortiert nach KW und Abholort."

    @classmethod
    def create_exports(cls):
        export_name = cls.NAME
        if CsvExport.objects.filter(name=export_name).exists():
            raise TemplateAlreadyExistsException(
                f'Ein CSV-Export mit dem Namen "{export_name}"  existiert bereits. Falls dieser neu erzeugt werden soll, bitte zuerst den alten Export-Eintrag aus der Liste löschen.'
            )

        column_ids = [
            JokerColumnProvider.COLUMN_ID_MEMBER_NUMBER,
            JokerColumnProvider.COLUMN_ID_MEMBER_LAST_NAME,
            JokerColumnProvider.COLUMN_ID_PICKUP_LOCATION,
            JokerColumnProvider.COLUMN_ID_PRODUCT_TYPES,
            JokerColumnProvider.COLUMN_ID_PRODUCTS,
            JokerColumnProvider.COLUMN_ID_CALENDAR_WEEK,
        ]

        CsvExport.objects.create(
            name=export_name,
            export_segment_id=JokerSegmentProvider.SEGMENT_ID_JOKER_THIS_GROWING_PERIOD,
            file_name="Joker Übersicht.csv",
            automated_export_cycle=AutomatedExportCycle.NEVER,
            automated_export_day=1,
            automated_export_hour=datetime.time(hour=23),
            separator=";",
            locale=LocaleChoices.DE,
            column_ids=column_ids,
            custom_column_names=[
                cls.get_default_column_name(column_id) for column_id in column_ids
            ],
        )

    @classmethod
    def get_default_column_name(cls, column_id: str):
        for column in JokerColumnProvider.get_joker_columns():
            if column.id == column_id:
                return column.display_name

        raise TapirImproperlyConfigured(f"No column with id {column_id} found")
