import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport, LocaleChoices
from tapir.payments.services.monthly_actual_income_column_provider import (
    MonthlyActualIncomeColumnProvider,
)
from tapir.payments.services.monthly_actual_income_segment_provider import (
    MonthlyActualIncomeSegmentProvider,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TemplatePaymentsByIncomeSource:
    ID = "payments_by_income_source"
    NAME = "Monatliche Übersicht eingezogene Zahlungen"
    DESCRIPTION = "Übersicht der eingezogene Zahlungen pro Quelle: Produktanteil, Solibeitrag, Liefergebühren..."

    @classmethod
    def create_exports(cls):
        export_name = cls.NAME
        if CsvExport.objects.filter(name=export_name).exists():
            raise TemplateAlreadyExistsException(
                f'Ein CSV-Export mit dem Namen "{export_name}"  existiert bereits. Falls dieser neu erzeugt werden soll, bitte zuerst den alten Export-Eintrag aus der Liste löschen.'
            )

        column_ids = [
            MonthlyActualIncomeColumnProvider.COLUMN_ID_SOURCE_NAME,
            MonthlyActualIncomeColumnProvider.COLUMN_ID_INCOME,
        ]

        CsvExport.objects.create(
            name=export_name,
            description="In diesem Export werden die monatlichen Lastschrift-Datensätze gemäß XML/CSV-Datei pro Produktanteil und sofern zutreffend Vereinsbeitrag/Genossenschaftsanteil (je nach Rechtsform) und Liefergebühren summiert dargestellt. Damit erkennt ihr, welcher Anteil der Zahlungen auf welchen Produktanteil bzw. Mitgliedschaftsteil entfällt.",
            export_segment_id=MonthlyActualIncomeSegmentProvider.SEGMENT_ID_MONTHLY_ACTUAL_INCOME,
            file_name="Eingezogene Zahlungen.csv",
            automated_export_cycle=AutomatedExportCycle.MONTHLY,
            automated_export_day=get_parameter_value(
                ParameterKeys.PAYMENT_DUE_DAY, cache={}
            ),
            automated_export_hour=datetime.time(hour=13),
            separator=";",
            locale=LocaleChoices.DE,
            column_ids=column_ids,
            custom_column_names=[
                cls.get_default_column_name(column_id) for column_id in column_ids
            ],
        )

    @classmethod
    def get_default_column_name(cls, column_id: str):
        for (
            column
        ) in MonthlyActualIncomeColumnProvider.get_monthly_actual_income_columns():
            if column.id == column_id:
                return column.display_name

        raise TapirImproperlyConfigured(f"No column with id {column_id} found")
